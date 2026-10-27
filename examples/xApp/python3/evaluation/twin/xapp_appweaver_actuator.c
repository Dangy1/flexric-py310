/*
 * SPDX-License-Identifier: LicenseRef-CSSL-1.0
 *
 * AppWeaver twin/live actuator xApp for ns-O-RAN-flexric (KPM v3.00, RC v1.03, E2AP v1.01).
 *
 * One process per simulation (ns-O-RAN gNBs accept a single KPM subscriber):
 *  - KPM capture: same CSV as xapp_kpm_capture ($KPM_CSV;
 *    wall_us,collect_start_us,node_type,nb_id,ue_imsi,meas,idx,value)
 *  - RC actuation: polls $RC_CMD_FILE every 100 ms; each new line is one command
 *        HO <imsi> <target_cell>      E2SM-RC style 3 / action 1 (handover control)
 *        OFF <cell>                   custom style 300 / CELL_OFF (cell switch-off)
 *    and appends "<wall_us> <command> sent|failed" to $RC_ACK_FILE.
 *
 * The KPM capture is copied from ~/flexric-taap/examples/xApp/c/appweaver/xapp_kpm_capture.c and the RC
 * message encoders from ~/flexric-taap/examples/xApp/c/orange/xapp_es_with_cell_util.c (RIC-TaaP xApps),
 * unchanged. The decisions (which UE, which cell) are taken outside, by the AppWeaver rApp models in
 * rapps/runtime.py, driven by evaluation/twin/run_twin_validation.py.
 */

#include "xApp/e42_xapp_api.h"
#include "sm/rc_sm/ie/ir/ran_param_struct.h"
#include "sm/rc_sm/ie/ir/ran_param_list.h"
#include "sm/rc_sm/rc_sm_id.h"
#include "sm/rc_sm/ie/rc_data_ie.h"
#include "util/time_now_us.h"
#include "util/alg_ds/ds/lock_guard/lock_guard.h"
#include "util/e.h"

#include <inttypes.h>
#include <pthread.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define MAX_NODES 32


typedef enum {
    CONNECTED_MODE_MOBILITY = 3,
    ENERGY_STATE = 300
} rc_ctrl_service_style_id_e;
  
typedef enum {
    CELL_OFF = '0',
    CELL_ON = '1',  
    CELL_SLEEP = '2',
} cell_state_e;
  
typedef enum {
    QOS_FLOW_ID_1 = 1,
    QOS_FLOW_ID_10 = 10
} qos_flow_id_e;

typedef enum {
    DRB_ID_3 = 3
} drb_id_e;
  
typedef enum {
    PDU_SESSION_ID_5 = 5
} pdu_session_id_e;

// ---------------------------------------------------------------- RC encoders (from xapp_es_with_cell_util.c)
static
e2sm_rc_ctrl_hdr_frmt_1_t gen_rc_ctrl_hdr_frmt_1(ue_id_e2sm_t ue_id, uint32_t ric_style_type,
                                                         uint16_t ctrl_act_id)
{
  e2sm_rc_ctrl_hdr_frmt_1_t dst = {0};

  // 6.2.2.6
  dst.ue_id = cp_ue_id_e2sm(&ue_id);

  dst.ric_style_type = ric_style_type;
  dst.ctrl_act_id = ctrl_act_id;

  return dst;
}

static
e2sm_rc_ctrl_hdr_t gen_rc_ctrl_hdr(e2sm_rc_ctrl_hdr_e hdr_frmt, ue_id_e2sm_t ue_id,
                                           uint32_t ric_style_type, uint16_t ctrl_act_id) 
{
  e2sm_rc_ctrl_hdr_t dst = {0};

  if (hdr_frmt == FORMAT_1_E2SM_RC_CTRL_HDR) {
    dst.format = FORMAT_1_E2SM_RC_CTRL_HDR;
    dst.frmt_1 = gen_rc_ctrl_hdr_frmt_1(ue_id, ric_style_type, ctrl_act_id);
  } else 
  {
    assert(0 != 0 && "not implemented the fill func for this ctrl hdr frmt");
  }

  return dst;
}

static
void set_EUTRA_CGI(seq_ran_param_t* EUTRA_CGI, const char targetcell)
{
  // Input validation
  assert(EUTRA_CGI != NULL);
  assert(targetcell >= '0' && targetcell <= '9');

  // Validate flag_false is allocated
  if (EUTRA_CGI->ran_param_val.flag_false == NULL) {
    EUTRA_CGI->ran_param_val.flag_false = calloc(1, sizeof(ran_parameter_value_t));
    assert(EUTRA_CGI->ran_param_val.flag_false != NULL && "Memory exhausted");
  }

  EUTRA_CGI->ran_param_val.flag_false->type = BIT_STRING_RAN_PARAMETER_VALUE;

  // Convert target cell to byte array
  byte_array_t target_ba = {0};
  target_ba.len = 1;
  target_ba.buf = malloc(sizeof(uint8_t));
  assert(target_ba.buf != NULL && "Memory exhausted");
  target_ba.buf[0] = targetcell;

  EUTRA_CGI->ran_param_val.flag_false->octet_str_ran.len = target_ba.len;
  EUTRA_CGI->ran_param_val.flag_false->octet_str_ran.buf = target_ba.buf;
}

static
void gen_Target_Primary_Cell_ID(seq_ran_param_t* Target_Primary_Cell_ID, char targetcell)
{
  // Target Primary Cell ID, STRUCTURE (len 1)

  Target_Primary_Cell_ID->ran_param_id = TARGET_PRIMARY_CELL_ID_8_4_4_1;
  Target_Primary_Cell_ID->ran_param_val.type = STRUCTURE_RAN_PARAMETER_VAL_TYPE;
  Target_Primary_Cell_ID->ran_param_val.strct = calloc(1, sizeof(ran_param_struct_t));
  assert(Target_Primary_Cell_ID->ran_param_val.strct != NULL && "Memory exhausted");
  Target_Primary_Cell_ID->ran_param_val.strct->sz_ran_param_struct = 1;
  Target_Primary_Cell_ID->ran_param_val.strct->ran_param_struct = calloc(1, sizeof(seq_ran_param_t));
  assert(Target_Primary_Cell_ID->ran_param_val.strct->ran_param_struct != NULL && "Memory exhausted");

  // > CHOICE Target Cell, STRUCTURE (len 2)
  seq_ran_param_t* CHOICE_Target_Cell = &Target_Primary_Cell_ID->ran_param_val.strct->ran_param_struct[0];
  CHOICE_Target_Cell->ran_param_id = CHOICE_TARGET_CELL_8_4_4_1;
  CHOICE_Target_Cell->ran_param_val.type = STRUCTURE_RAN_PARAMETER_VAL_TYPE;
  CHOICE_Target_Cell->ran_param_val.strct = calloc(1, sizeof(ran_param_struct_t));
  assert(CHOICE_Target_Cell->ran_param_val.strct != NULL && "Memory exhausted");
  CHOICE_Target_Cell->ran_param_val.strct->sz_ran_param_struct = 2;
  CHOICE_Target_Cell->ran_param_val.strct->ran_param_struct = calloc(2, sizeof(seq_ran_param_t));
  assert(CHOICE_Target_Cell->ran_param_val.strct->ran_param_struct != NULL && "Memory exhausted");

  // >>  NR Cell, STRUCTURE (len 1))
  seq_ran_param_t* NR_Cell = &CHOICE_Target_Cell->ran_param_val.strct->ran_param_struct[0];
  NR_Cell->ran_param_id = NR_CELL_8_4_4_1;
  NR_Cell->ran_param_val.type = STRUCTURE_RAN_PARAMETER_VAL_TYPE;
  NR_Cell->ran_param_val.strct = calloc(1, sizeof(ran_param_struct_t));
  assert(NR_Cell->ran_param_val.strct != NULL && "Memory exhausted");
  NR_Cell->ran_param_val.strct->sz_ran_param_struct = 1;
  NR_Cell->ran_param_val.strct->ran_param_struct = calloc(1, sizeof(seq_ran_param_t));

  // >>> NR CGI, ELEMENT   NR CGI is usually written in the format: PLMN ID + NR Cell Identity.
  seq_ran_param_t* NR_CGI = &NR_Cell->ran_param_val.strct->ran_param_struct[0];
  NR_CGI->ran_param_id = NR_CGI_8_4_4_1;
  NR_CGI->ran_param_val.type = ELEMENT_KEY_FLAG_FALSE_RAN_PARAMETER_VAL_TYPE;
  NR_CGI->ran_param_val.flag_false = calloc(1, sizeof(ran_parameter_value_t));
  assert(NR_CGI->ran_param_val.flag_false != NULL && "Memory exhausted");
  NR_CGI->ran_param_val.flag_false->type = BIT_STRING_RAN_PARAMETER_VALUE;
  // NR_CGI->ran_param_val.flag_false->int_ran=  TARGET_CELL;
  char nr_cgi_str[1] = {targetcell};

  byte_array_t nr_cgi = cp_str_to_ba(nr_cgi_str);
  NR_CGI->ran_param_val.flag_false->octet_str_ran.len = nr_cgi.len;
  NR_CGI->ran_param_val.flag_false->octet_str_ran.buf = nr_cgi.buf;

  // >>E-UTRA Cell, STRUCTURE (len 1)
  seq_ran_param_t* EUTRA_Cell = &CHOICE_Target_Cell->ran_param_val.strct->ran_param_struct[1];
  EUTRA_Cell->ran_param_id = EUTRA_CELL_8_4_4_1;
  EUTRA_Cell->ran_param_val.type = STRUCTURE_RAN_PARAMETER_VAL_TYPE;
  EUTRA_Cell->ran_param_val.strct = calloc(1, sizeof(ran_param_struct_t));
  assert(EUTRA_Cell->ran_param_val.strct != NULL && "Memory exhausted");
  EUTRA_Cell->ran_param_val.strct->sz_ran_param_struct = 1;
  EUTRA_Cell->ran_param_val.strct->ran_param_struct = calloc(1, sizeof(seq_ran_param_t));

  // >>>E-UTRA CGI, ELEMENT  The E-UTRA CGI is typically written in the format: PLMN ID + E-UTRAN Cell Identity.
  seq_ran_param_t* EUTRA_CGI = &EUTRA_Cell->ran_param_val.strct->ran_param_struct[0];
  EUTRA_CGI->ran_param_id = EUTRA_CGI_8_4_4_1;
  EUTRA_CGI->ran_param_val.type = ELEMENT_KEY_FLAG_FALSE_RAN_PARAMETER_VAL_TYPE;
  EUTRA_CGI->ran_param_val.flag_false = calloc(1, sizeof(ran_parameter_value_t));
  assert(EUTRA_CGI->ran_param_val.flag_false != NULL && "Memory exhausted");
  EUTRA_CGI->ran_param_val.flag_false->type = BIT_STRING_RAN_PARAMETER_VALUE;

  set_EUTRA_CGI(EUTRA_CGI, targetcell);

  // char eUTRA_cgi_str [2] ;
  // eUTRA_cgi_str[0] = targetcell;
  // eUTRA_cgi_str [1] = '\0';

  // byte_array_t eUTRA_cgi = cp_str_to_ba(eUTRA_cgi_str);
  // EUTRA_CGI->ran_param_val.flag_false->octet_str_ran.len = eUTRA_cgi.len;
  // EUTRA_CGI->ran_param_val.flag_false->octet_str_ran.buf = eUTRA_cgi.buf;
  return;
}

static
void gen_List_of_PDU_sessions_for_handover(seq_ran_param_t* List_PDU_sessions_ho)
{
  int num_PDU_session = 1;

  // List of PDU sessions for handover, LIST (len 1)
  List_PDU_sessions_ho->ran_param_id = LIST_OF_PDU_SESSIONS_FOR_HANDOVER_8_4_4_1;
  List_PDU_sessions_ho->ran_param_val.type = LIST_RAN_PARAMETER_VAL_TYPE;
  List_PDU_sessions_ho->ran_param_val.lst = calloc(1, sizeof(ran_param_list_t));
  assert(List_PDU_sessions_ho->ran_param_val.lst != NULL && "Memory exhausted");
  List_PDU_sessions_ho->ran_param_val.lst->sz_lst_ran_param = num_PDU_session;
  List_PDU_sessions_ho->ran_param_val.lst->lst_ran_param = calloc(num_PDU_session, sizeof(lst_ran_param_t));
  assert(List_PDU_sessions_ho->ran_param_val.lst->lst_ran_param != NULL && "Memory exhausted");

  // > PDU session Item for handover, STRUCTURE (len 2)
  lst_ran_param_t* PDU_session_item = &List_PDU_sessions_ho->ran_param_val.lst->lst_ran_param[0];
  PDU_session_item->ran_param_struct.sz_ran_param_struct = 2;
  PDU_session_item->ran_param_struct.ran_param_struct = calloc(2, sizeof(seq_ran_param_t));
  assert(PDU_session_item->ran_param_struct.ran_param_struct != NULL && "Memory exhausted");

  // >> PDU Session ID, ELEMENT
  seq_ran_param_t* PDU_Session_ID = &PDU_session_item->ran_param_struct.ran_param_struct[0];
  PDU_Session_ID->ran_param_id = PDU_SESSION_ID_8_4_4_1;
  PDU_Session_ID->ran_param_val.type = ELEMENT_KEY_FLAG_TRUE_RAN_PARAMETER_VAL_TYPE;
  PDU_Session_ID->ran_param_val.flag_false = calloc(1, sizeof(ran_parameter_value_t));
  assert(PDU_Session_ID->ran_param_val.flag_false != NULL && "Memory exhausted");
  PDU_Session_ID->ran_param_val.flag_false->type = OCTET_STRING_RAN_PARAMETER_VALUE;

  // Use enum for PDU Session ID
  char pduid_str[2];
  snprintf(pduid_str, sizeof(pduid_str), "%d", PDU_SESSION_ID_5);
  byte_array_t pduid = cp_str_to_ba(pduid_str);
  PDU_Session_ID->ran_param_val.flag_false->octet_str_ran.len = pduid.len;
  PDU_Session_ID->ran_param_val.flag_false->octet_str_ran.buf = pduid.buf;

  // >> List of QoS flows in the PDU session, LIST (len 1)
  seq_ran_param_t* List_of_QoS_flows = &PDU_session_item->ran_param_struct.ran_param_struct[1];
  List_of_QoS_flows->ran_param_id = LIST_OF_QOS_FLOWS_IN_THE_PDU_SESSION_8_4_4_1;
  List_of_QoS_flows->ran_param_val.type = LIST_RAN_PARAMETER_VAL_TYPE;
  List_of_QoS_flows->ran_param_val.lst = calloc(1, sizeof(ran_param_list_t));
  assert(List_of_QoS_flows->ran_param_val.lst != NULL && "Memory exhausted");
  List_of_QoS_flows->ran_param_val.lst->sz_lst_ran_param = 1;
  List_of_QoS_flows->ran_param_val.lst->lst_ran_param = calloc(1, sizeof(lst_ran_param_t));
  assert(List_of_QoS_flows->ran_param_val.lst->lst_ran_param != NULL && "Memory exhausted");

  // >>> QoS flow Item, STRUCTURE (len 1)
  lst_ran_param_t* QoS_flow_Item = &List_of_QoS_flows->ran_param_val.lst->lst_ran_param[0];
  QoS_flow_Item->ran_param_struct.sz_ran_param_struct = 1;
  QoS_flow_Item->ran_param_struct.ran_param_struct = calloc(1, sizeof(seq_ran_param_t));
  assert(QoS_flow_Item->ran_param_struct.ran_param_struct != NULL && "Memory exhausted");

  // >>>> QoS Flow Identifier, ELEMENT
  seq_ran_param_t* QoS_Flow_Id = &QoS_flow_Item->ran_param_struct.ran_param_struct[0];
  QoS_Flow_Id->ran_param_id = QOS_FLOW_IDENTIFIER_8_4_4_1;
  QoS_Flow_Id->ran_param_val.type = ELEMENT_KEY_FLAG_TRUE_RAN_PARAMETER_VAL_TYPE;
  QoS_Flow_Id->ran_param_val.flag_false = calloc(1, sizeof(ran_parameter_value_t));
  assert(QoS_Flow_Id->ran_param_val.flag_false != NULL && "Memory exhausted");
  QoS_Flow_Id->ran_param_val.flag_false->type = OCTET_STRING_RAN_PARAMETER_VALUE;

  // Use enum for QoS Flow ID
  char qosid_str[3];
  snprintf(qosid_str, sizeof(qosid_str), "%d", QOS_FLOW_ID_1);
  byte_array_t qosid = cp_str_to_ba(qosid_str);
  QoS_Flow_Id->ran_param_val.flag_false->octet_str_ran.len = qosid.len;
  QoS_Flow_Id->ran_param_val.flag_false->octet_str_ran.buf = qosid.buf;

  return;
}

static
void gen_List_of_DRBs_for_handover(seq_ran_param_t* List_DRBs_ho)
{
  int num_DRBs = 1;
  // List of DRBs for handover, LIST (len 1)
  List_DRBs_ho->ran_param_id = LIST_OF_DRBS_FOR_HANDOVER_8_4_4_1;
  List_DRBs_ho->ran_param_val.type = LIST_RAN_PARAMETER_VAL_TYPE;
  List_DRBs_ho->ran_param_val.lst = calloc(1, sizeof(ran_param_list_t));
  assert(List_DRBs_ho->ran_param_val.lst != NULL && "Memory exhausted");
  List_DRBs_ho->ran_param_val.lst->sz_lst_ran_param = num_DRBs;
  List_DRBs_ho->ran_param_val.lst->lst_ran_param = calloc(num_DRBs, sizeof(lst_ran_param_t));
  assert(List_DRBs_ho->ran_param_val.lst->lst_ran_param != NULL && "Memory exhausted");

  // > DRB item for handover, STRUCTURE (len 2)
  lst_ran_param_t* DRB_item_ho = (lst_ran_param_t*)&List_DRBs_ho->ran_param_val.strct->ran_param_struct[0];

  DRB_item_ho->ran_param_struct.sz_ran_param_struct = 2;
  DRB_item_ho->ran_param_struct.ran_param_struct = calloc(2, sizeof(seq_ran_param_t));
  assert(DRB_item_ho->ran_param_struct.ran_param_struct != NULL && "Memory exhausted");

  // >> DRB ID, ELEMENT
  seq_ran_param_t* DRB_ID = &DRB_item_ho->ran_param_struct.ran_param_struct[0];
  DRB_ID->ran_param_id = DRB_ID_8_4_4_1;
  DRB_ID->ran_param_val.type = ELEMENT_KEY_FLAG_TRUE_RAN_PARAMETER_VAL_TYPE;
  DRB_ID->ran_param_val.flag_false = calloc(1, sizeof(ran_parameter_value_t));
  assert(DRB_ID->ran_param_val.flag_false != NULL && "Memory exhausted");
  DRB_ID->ran_param_val.flag_false->type = OCTET_STRING_RAN_PARAMETER_VALUE;
  char DRB_ID_str[] = "3";
  byte_array_t drpID = cp_str_to_ba(DRB_ID_str);
  DRB_ID->ran_param_val.flag_false->octet_str_ran.len = drpID.len;
  DRB_ID->ran_param_val.flag_false->octet_str_ran.buf = drpID.buf;

  // >> List of QoS flows in the DRB, LIST (len 1)
  seq_ran_param_t* List_of_QoS_flows = &DRB_item_ho->ran_param_struct.ran_param_struct[1];  //////.....//////
  List_of_QoS_flows->ran_param_id = LIST_OF_QOS_FLOWS_IN_THE_DRB_8_4_4_1;
  List_of_QoS_flows->ran_param_val.type = LIST_RAN_PARAMETER_VAL_TYPE;
  List_of_QoS_flows->ran_param_val.lst = calloc(1, sizeof(ran_param_list_t));
  assert(List_of_QoS_flows->ran_param_val.lst != NULL && "Memory exhausted");
  List_of_QoS_flows->ran_param_val.lst->sz_lst_ran_param = 1;
  List_of_QoS_flows->ran_param_val.lst->lst_ran_param = calloc(1, sizeof(lst_ran_param_t));
  assert(List_of_QoS_flows->ran_param_val.lst->lst_ran_param != NULL && "Memory exhausted");

  // >>>QoS flow Item, STRUCTURE (len 1)
  lst_ran_param_t* QoS_flow_Item = &List_of_QoS_flows->ran_param_val.lst->lst_ran_param[0];
  QoS_flow_Item->ran_param_struct.sz_ran_param_struct = 1;
  QoS_flow_Item->ran_param_struct.ran_param_struct = calloc(1, sizeof(seq_ran_param_t));
  assert(QoS_flow_Item->ran_param_struct.ran_param_struct != NULL && "Memory exhausted");

  // >>>>QoS Flow Identifier, ELEMENT
  seq_ran_param_t* QoS_Flow_Id = &QoS_flow_Item->ran_param_struct.ran_param_struct[0];
  QoS_Flow_Id->ran_param_id = QOS_FLOW_IDENTIFIER_8_4_4_1;
  QoS_Flow_Id->ran_param_val.type = ELEMENT_KEY_FLAG_TRUE_RAN_PARAMETER_VAL_TYPE;
  QoS_Flow_Id->ran_param_val.flag_false = calloc(1, sizeof(ran_parameter_value_t));
  assert(QoS_Flow_Id->ran_param_val.flag_false != NULL && "Memory exhausted");
  QoS_Flow_Id->ran_param_val.flag_false->type = OCTET_STRING_RAN_PARAMETER_VALUE;
  char QFI_str[] = "10";
  byte_array_t QFI = cp_str_to_ba(QFI_str);
  QoS_Flow_Id->ran_param_val.flag_false->octet_str_ran.len = QFI.len;
  QoS_Flow_Id->ran_param_val.flag_false->octet_str_ran.buf = QFI.buf;

  return;
}

static
void gen_List_of_Secondary_cells_to_be_setup(seq_ran_param_t* List_num_2ndCells)
{
  int num_2ndCells = 1;
  // List of Secondary cells to be setup, LIST (len 1)
  List_num_2ndCells->ran_param_id = LIST_OF_SECONDARY_CELLS_TO_BE_SETUP_8_4_4_1;
  List_num_2ndCells->ran_param_val.type = LIST_RAN_PARAMETER_VAL_TYPE;
  List_num_2ndCells->ran_param_val.lst = calloc(1, sizeof(ran_param_list_t));
  assert(List_num_2ndCells->ran_param_val.lst != NULL && "Memory exhausted");
  List_num_2ndCells->ran_param_val.lst->sz_lst_ran_param = num_2ndCells;
  List_num_2ndCells->ran_param_val.lst->lst_ran_param = calloc(num_2ndCells, sizeof(lst_ran_param_t));
  assert(List_num_2ndCells->ran_param_val.lst->lst_ran_param != NULL && "Memory exhausted");

  // >Secondary cell Item to be setup, STRUCTURE (len 1)
  lst_ran_param_t* secCell_item = (lst_ran_param_t*)&List_num_2ndCells->ran_param_val.strct->ran_param_struct[0];

  secCell_item->ran_param_struct.sz_ran_param_struct = 1;
  secCell_item->ran_param_struct.ran_param_struct = calloc(1, sizeof(seq_ran_param_t));
  assert(secCell_item->ran_param_struct.ran_param_struct != NULL && "Memory exhausted");

  // >>Secondary cell ID, ELEMENT
  seq_ran_param_t* secCell_Id = &secCell_item->ran_param_struct.ran_param_struct[0];
  secCell_Id->ran_param_id = SECONDARY_CELL_ID_8_4_4_1;
  secCell_Id->ran_param_val.type = ELEMENT_KEY_FLAG_FALSE_RAN_PARAMETER_VAL_TYPE;
  secCell_Id->ran_param_val.flag_false = calloc(1, sizeof(ran_parameter_value_t));
  assert(secCell_Id->ran_param_val.flag_false != NULL && "Memory exhausted");
  secCell_Id->ran_param_val.flag_false->type = OCTET_STRING_RAN_PARAMETER_VALUE;
  char cellID_str[] = "0";
  byte_array_t QFI = cp_str_to_ba(cellID_str);
  secCell_Id->ran_param_val.flag_false->octet_str_ran.len = QFI.len;
  secCell_Id->ran_param_val.flag_false->octet_str_ran.buf = QFI.buf;

  return;
}

static
e2sm_rc_ctrl_msg_frmt_1_t gen_rc_ctrl_msg_frmt_1_Handover_Control(char targetcell)
{
  e2sm_rc_ctrl_msg_frmt_1_t dst = {0};
  // 8.4.4.1

  // Target Primary Cell ID, STRUCTURE (len 1)
  // > CHOICE Target Cell, STRUCTURE (len 2)
  // >>  NR Cell, STRUCTURE (len 1))
  // >>> NR CGI, ELEMENT
  // >>E-UTRA Cell, STRUCTURE (len 1)
  // >>>E-UTRA CGI, ELEMENT

  // List of PDU sessions for handover, LIST (len 1)
  // >PDU session Item for handover, STRUCTURE (len 2)
  // >>PDU Session ID, ELEMENT
  // >>List of QoS flows in the PDU session, LIST (len 1)
  // >>>QoS flow Item, STRUCTURE (len 1)
  // >>>>QoS Flow Identifier, ELEMENT

  // List of DRBs for handover, LIST (len 1)
  // > DRB item for handover, STRUCTURE (len 2)
  // >> DRB ID, ELEMENT
  // >> List of QoS flows in the DRB, LIST (len 1)
  // >>> QoS flow Item, STRUCTURE (len 1)
  // >>>> QoS flow Identifier, ELEMENT

  // List of Secondary cells to be setup, LIST (len 1)
  // >Secondary cell Item to be setup, STRUCTURE (len 1)
  // >>Secondary cell ID, ELEMENT

  dst.sz_ran_param = 4;
  dst.ran_param = calloc(4, sizeof(seq_ran_param_t));
  assert(dst.ran_param != NULL && "Memory exhausted");

  gen_Target_Primary_Cell_ID(&dst.ran_param[0], targetcell);
  gen_List_of_PDU_sessions_for_handover(&dst.ran_param[1]);
  gen_List_of_DRBs_for_handover(&dst.ran_param[2]);
  gen_List_of_Secondary_cells_to_be_setup(&dst.ran_param[3]);

  return dst;
}

static
e2sm_rc_ctrl_msg_frmt_1_t gen_rc_ctrl_msg_frmt_1_cell_trigger(char targetcell)
{
  e2sm_rc_ctrl_msg_frmt_1_t dst = {0};
  // 8.4.4.1

  // Target Primary Cell ID, STRUCTURE (len 1)
  // > CHOICE Target Cell, STRUCTURE (len 2)
  // >>  NR Cell, STRUCTURE (len 1))
  // >>> NR CGI, ELEMENT
  // >>E-UTRA Cell, STRUCTURE (len 1)
  // >>>E-UTRA CGI, ELEMENT
  dst.sz_ran_param = 1;
  dst.ran_param = calloc(4, sizeof(seq_ran_param_t));
  assert(dst.ran_param != NULL && "Memory exhausted");

  gen_Target_Primary_Cell_ID(&dst.ran_param[0], targetcell);
  return dst;
}

static
e2sm_rc_ctrl_msg_t gen_handover_rc_ctrl_msg(e2sm_rc_ctrl_msg_e msg_frmt, uint8_t targetcell)
{
  e2sm_rc_ctrl_msg_t dst = {0};

  if (msg_frmt == FORMAT_1_E2SM_RC_CTRL_MSG) {
    dst.format = msg_frmt;
    dst.frmt_1 = gen_rc_ctrl_msg_frmt_1_Handover_Control(targetcell);
  } else 
  {
    assert(0 != 0 && "not implemented the fill func for this ctrl msg frmt");
  }

  return dst;
}

static
e2sm_rc_ctrl_msg_t gen_cell_trigger_rc_ctrl_msg(e2sm_rc_ctrl_msg_e msg_frmt, char targetcell)
{
  e2sm_rc_ctrl_msg_t dst = {0};

  if (msg_frmt == FORMAT_1_E2SM_RC_CTRL_MSG) {
    dst.format = msg_frmt;
    dst.frmt_1 = gen_rc_ctrl_msg_frmt_1_cell_trigger(targetcell);
  } else 
  {
    assert(0 != 0 && "not implemented the fill func for this ctrl msg frmt");
  }

  return dst;
}

static
ue_id_e2sm_t gen_rc_ue_id(ue_id_e2sm_e type, int ueid)
{
  ue_id_e2sm_t ue_id = {0};
  if (type == GNB_UE_ID_E2SM) {
    ue_id.type = GNB_UE_ID_E2SM;
    ue_id.gnb.ran_ue_id = (uint64_t*)malloc(sizeof(uint64_t));
    *(ue_id.gnb.ran_ue_id) = ueid;
  } else 
  {
    assert(0 != 0 && "not supported UE ID type");
  }
  return ue_id;
}

// ---------------------------------------------------------------- KPM capture (from xapp_kpm_capture.c)
static
uint64_t const period_ms = 100;

static
pthread_mutex_t mtx = PTHREAD_MUTEX_INITIALIZER;

static
e2_node_arr_xapp_t nodes;

static
volatile sig_atomic_t stop = 0;

// CSV sink: $KPM_CSV if set (the SDK also logs to stdout), else stdout
static
FILE* csv;

static
void on_signal(int sig)
{
  (void)sig;
  stop = 1;
}

// ns-O-RAN packs the IMSI string ("00004") little-endian into amf_UE_NGAP_ID
static
int64_t ue_id_val(ue_id_e2sm_t const* id)
{
  if (id->type != GNB_UE_ID_E2SM)
    return -2;
  uint64_t const v = id->gnb.amf_ue_ngap_id;
  int64_t imsi = 0;
  int digits = 0;
  for (int k = 0; k < 8; k++) {
    char const c = (char)((v >> (8 * k)) & 0xff);
    if (c == 0)
      break;
    if (c < '0' || c > '9')
      return (int64_t)v;
    imsi = imsi * 10 + (c - '0');
    digits++;
  }
  return digits > 0 ? imsi : (int64_t)v;
}

static
void print_rec(global_e2_node_id_t const* id, int64_t ue, uint64_t wall, uint64_t start,
               meas_type_t const* type, size_t idx, meas_record_lst_t const* r)
{
  if (type->type != NAME_MEAS_TYPE || type->name.len == 0)
    return;
  char* name = cp_ba_to_str(type->name);
  fprintf(csv, "%" PRIu64 ",%" PRIu64 ",%d,%u,%" PRId64 ",%s,%zu,", wall, start, id->type, id->nb_id.nb_id, ue, name, idx);
  if (r->value == INTEGER_MEAS_VALUE)
    fprintf(csv, "%u\n", r->int_val);
  else if (r->value == REAL_MEAS_VALUE)
    fprintf(csv, "%.6f\n", r->real_val);
  else
    fprintf(csv, "\n");
  free(name);
}

static
void print_frm_1(int node, int64_t ue, uint64_t wall, uint64_t start, kpm_ind_msg_format_1_t const* msg)
{
  global_e2_node_id_t const* id = &nodes.n[node].id;
  if (getenv("KPM_DEBUG") != NULL) {
    fprintf(stderr, "[DBG] nb %u ue %" PRId64 " meas_info %zu meas_data %zu |", id->nb_id.nb_id, ue, msg->meas_info_lst_len, msg->meas_data_lst_len);
    for (size_t i = 0; i < msg->meas_info_lst_len; i++) {
      char* n = msg->meas_info_lst[i].meas_type.name.len ? cp_ba_to_str(msg->meas_info_lst[i].meas_type.name) : strdup("?");
      fprintf(stderr, " %s(lbl %zu)", n, msg->meas_info_lst[i].label_info_lst_len);
      free(n);
    }
    fprintf(stderr, " | rec/data:");
    for (size_t j = 0; j < msg->meas_data_lst_len; j++)
      fprintf(stderr, " %zu", msg->meas_data_lst[j].meas_record_len);
    fprintf(stderr, "\n");
  }

  if (msg->meas_info_lst_len == msg->meas_data_lst_len && msg->meas_info_lst_len > 1) {
    // ns-O-RAN layout: meas_data[i] holds all records of meas_info[i]
    // (e.g. one record per neighbour cell for L3neighSINRListOf_*)
    for (size_t i = 0; i < msg->meas_info_lst_len; i++) {
      meas_data_lst_t const* data = &msg->meas_data_lst[i];
      for (size_t r = 0; r < data->meas_record_len; r++)
        print_rec(id, ue, wall, start, &msg->meas_info_lst[i].meas_type, r, &data->meas_record_lst[r]);
    }
    return;
  }

  // Spec layout: each meas_data item is one granularity period with one record per (meas, label)
  for (size_t j = 0; j < msg->meas_data_lst_len; j++) {
    meas_data_lst_t const* data = &msg->meas_data_lst[j];
    size_t rec = 0;
    for (size_t i = 0; i < msg->meas_info_lst_len; i++) {
      meas_info_format_1_lst_t const* info = &msg->meas_info_lst[i];
      for (size_t z = 0; z < info->label_info_lst_len && rec < data->meas_record_len; z++, rec++)
        print_rec(id, ue, wall, start, &info->meas_type, j, &data->meas_record_lst[rec]);
    }
  }
}

static
void handle_ind(int node, sm_ag_if_rd_t const* rd)
{
  assert(rd->type == INDICATION_MSG_AGENT_IF_ANS_V0);
  assert(rd->ind.type == KPM_STATS_V3_0);
  kpm_ind_data_t const* ind = &rd->ind.kpm.ind;
  uint64_t const wall = time_now_us();
  uint64_t const start = ind->hdr.kpm_ric_ind_hdr_format_1.collectStartTime;

  lock_guard(&mtx);
  if (ind->msg.type == FORMAT_1_INDICATION_MESSAGE) {
    print_frm_1(node, -1, wall, start, &ind->msg.frm_1);
  } else if (ind->msg.type == FORMAT_3_INDICATION_MESSAGE) {
    kpm_ind_msg_format_3_t const* f3 = &ind->msg.frm_3;
    for (size_t i = 0; i < f3->ue_meas_report_lst_len; i++)
      print_frm_1(node, ue_id_val(&f3->meas_report_per_ue[i].ue_meas_report_lst), wall, start,
                  &f3->meas_report_per_ue[i].ind_msg_format_1);
  }
  fflush(csv);
}

// The SDK callback carries no E2 node id, so give every node its own trampoline
#define CB(N) static void cb_##N(sm_ag_if_rd_t const* rd) { handle_ind(N, rd); }
CB(0) CB(1) CB(2) CB(3) CB(4) CB(5) CB(6) CB(7) CB(8) CB(9) CB(10) CB(11) CB(12) CB(13) CB(14) CB(15)
CB(16) CB(17) CB(18) CB(19) CB(20) CB(21) CB(22) CB(23) CB(24) CB(25) CB(26) CB(27) CB(28) CB(29) CB(30) CB(31)
#undef CB

static
sm_cb const node_cb[MAX_NODES] = {
  cb_0, cb_1, cb_2, cb_3, cb_4, cb_5, cb_6, cb_7, cb_8, cb_9, cb_10, cb_11, cb_12, cb_13, cb_14, cb_15,
  cb_16, cb_17, cb_18, cb_19, cb_20, cb_21, cb_22, cb_23, cb_24, cb_25, cb_26, cb_27, cb_28, cb_29, cb_30, cb_31,
};

static
label_info_lst_t no_label(void)
{
  label_info_lst_t l = {0};
  l.noLabel = ecalloc(1, sizeof(enum_value_e));
  *l.noLabel = TRUE_ENUM_VALUE;
  return l;
}

static
kpm_act_def_format_1_t fill_frm_1(ric_report_style_item_t const* item)
{
  kpm_act_def_format_1_t f1 = {0};
  f1.meas_info_lst_len = item->meas_info_for_action_lst_len;
  f1.meas_info_lst = ecalloc(f1.meas_info_lst_len, sizeof(meas_info_format_1_lst_t));
  for (size_t i = 0; i < f1.meas_info_lst_len; i++) {
    meas_info_format_1_lst_t* m = &f1.meas_info_lst[i];
    m->meas_type.type = NAME_MEAS_TYPE;
    m->meas_type.name = copy_byte_array(item->meas_info_for_action_lst[i].name);
    m->label_info_lst_len = 1;
    m->label_info_lst = ecalloc(1, sizeof(label_info_lst_t));
    m->label_info_lst[0] = no_label();
  }
  f1.gran_period_ms = period_ms;
  f1.cell_global_id = NULL;
  f1.meas_bin_range_info_lst_len = 0;
  f1.meas_bin_info_lst = NULL;
  return f1;
}

static
bool gen_act_def(ric_report_style_item_t const* item, kpm_act_def_t* ad)
{
  switch (item->act_def_format_type) {
    case FORMAT_1_ACTION_DEFINITION:
      ad->type = FORMAT_1_ACTION_DEFINITION;
      ad->frm_1 = fill_frm_1(item);
      return true;
    case FORMAT_4_ACTION_DEFINITION: {
      // Same matching condition shape as the shipped xapp_es_with_cell_util (IsStat < N)
      ad->type = FORMAT_4_ACTION_DEFINITION;
      ad->frm_4.matching_cond_lst_len = 1;
      ad->frm_4.matching_cond_lst = ecalloc(1, sizeof(matching_condition_format_4_lst_t));
      test_info_lst_t* t = &ad->frm_4.matching_cond_lst[0].test_info_lst;
      t->test_cond_type = IsStat_TEST_COND_TYPE;
      t->IsStat = TRUE_TEST_COND_TYPE;
      t->test_cond = ecalloc(1, sizeof(test_cond_e));
      *t->test_cond = LESSTHAN_TEST_COND;
      t->test_cond_value = ecalloc(1, sizeof(test_cond_value_t));
      t->test_cond_value->type = INTEGER_TEST_COND_VALUE;
      t->test_cond_value->int_value = ecalloc(1, sizeof(int64_t));
      char const* lt = getenv("KPM_PRB_LT");
      *t->test_cond_value->int_value = lt != NULL ? atoi(lt) : 101;
      ad->frm_4.action_def_format_1 = fill_frm_1(item);
      return true;
    }
    default:
      return false;
  }
}


// ---------------------------------------------------------------- RC actuation (AppWeaver)
static
bool send_rc(e2_node_arr_xapp_t const* arr, char const* verb, int a, int b)
{
  rc_ctrl_req_data_t rc_ctrl = {0};
  bool sent = false;
  if (strcmp(verb, "HO") == 0) {
    if (b < 1 || b > 9)
      return false;
    ue_id_e2sm_t ue = gen_rc_ue_id(GNB_UE_ID_E2SM, a);
    rc_ctrl.hdr = gen_rc_ctrl_hdr(FORMAT_1_E2SM_RC_CTRL_HDR, ue, CONNECTED_MODE_MOBILITY, HANDOVER_CONTROL_7_6_4_1);
    rc_ctrl.msg = gen_handover_rc_ctrl_msg(FORMAT_1_E2SM_RC_CTRL_MSG, (uint8_t)('0' + b));
    free_ue_id_e2sm(&ue);
    // As in the shipped ES xApp: every node receives it, the UE's serving cell executes it
    for (size_t i = 0; i < arr->len; ++i)
      sent |= control_sm_xapp_api(&arr->n[i].id, SM_RC_ID, &rc_ctrl).success;
  } else if (strcmp(verb, "OFF") == 0) {
    if (a < 1 || a > 9)
      return false;
    ue_id_e2sm_t ue = gen_rc_ue_id(GNB_UE_ID_E2SM, 0);
    rc_ctrl.hdr = gen_rc_ctrl_hdr(FORMAT_1_E2SM_RC_CTRL_HDR, ue, ENERGY_STATE, CELL_OFF);
    rc_ctrl.msg = gen_cell_trigger_rc_ctrl_msg(FORMAT_1_E2SM_RC_CTRL_MSG, (char)('0' + a));
    free_ue_id_e2sm(&ue);
    sent = control_sm_xapp_api(&arr->n[0].id, SM_RC_ID, &rc_ctrl).success;
  } else {
    return false;
  }
  free_rc_ctrl_req_data(&rc_ctrl);
  return sent;
}

// Execute every command line appended to $RC_CMD_FILE since the last poll
static
void poll_commands(e2_node_arr_xapp_t const* arr, char const* cmd_path, FILE* ack, long* offset)
{
  if (cmd_path == NULL)
    return;
  FILE* f = fopen(cmd_path, "r");
  if (f == NULL)
    return;
  fseek(f, *offset, SEEK_SET);
  char line[128];
  while (fgets(line, sizeof(line), f) != NULL) {
    if (strchr(line, '\n') == NULL)
      break;  // partially written line: retry next poll
    *offset = ftell(f);
    char verb[8] = {0};
    int a = 0, b = 0;
    int const n = sscanf(line, "%7s %d %d", verb, &a, &b);
    if (n < 2)
      continue;
    bool const ok = send_rc(arr, verb, a, b);
    line[strcspn(line, "\n")] = 0;
    fprintf(stderr, "[ACTUATOR]: %s -> %s\n", line, ok ? "sent" : "failed");
    if (ack != NULL) {
      fprintf(ack, "%" PRIu64 " %s %s\n", time_now_us(), line, ok ? "sent" : "failed");
      fflush(ack);
    }
  }
  fclose(f);
}

int main(int argc, char* argv[])
{
  int duration_s = 0;
  if (argc >= 3 && strcmp(argv[argc - 2], "-t") == 0) {
    duration_s = atoi(argv[argc - 1]);
    argc -= 2;
  }

  fr_args_t args = init_fr_args(argc, argv);
  signal(SIGINT, on_signal);
  signal(SIGTERM, on_signal);

  init_xapp_api(&args);
  sleep(1);

  nodes = e2_nodes_xapp_api();
  assert(nodes.len > 0);
  assert(nodes.len <= MAX_NODES);
  fprintf(stderr, "[ACTUATOR]: connected E2 nodes = %d\n", nodes.len);

  int const KPM_ran_function = 2;
  sm_ans_xapp_t* hndl[MAX_NODES] = {0};
  size_t n_hndl[MAX_NODES] = {0};

  char const* csv_path = getenv("KPM_CSV");
  csv = csv_path != NULL ? fopen(csv_path, "w") : stdout;
  assert(csv != NULL && "Cannot open $KPM_CSV");
  fprintf(csv, "wall_us,collect_start_us,node_type,nb_id,ue_imsi,meas,idx,value\n");
  fflush(csv);

  for (size_t i = 0; i < nodes.len; i++) {
    e2_node_connected_xapp_t* n = &nodes.n[i];
    for (size_t k = 0; k < n->len_rf; k++) {
      if (n->rf[k].id != KPM_ran_function || n->rf[k].defn.type != KPM_RAN_FUNC_DEF_E)
        continue;
      kpm_ran_function_def_t const* def = &n->rf[k].defn.kpm;
      hndl[i] = ecalloc(def->sz_ric_report_style_list, sizeof(sm_ans_xapp_t));
      n_hndl[i] = def->sz_ric_report_style_list;
      for (size_t j = 0; j < def->sz_ric_report_style_list; j++) {
        kpm_sub_data_t sub = {0};
        sub.ev_trg_def.type = FORMAT_1_RIC_EVENT_TRIGGER;
        sub.ev_trg_def.kpm_ric_event_trigger_format_1.report_period_ms = period_ms;
        sub.sz_ad = 1;
        sub.ad = ecalloc(1, sizeof(kpm_act_def_t));
        if (!gen_act_def(&def->ric_report_style_list[j], sub.ad)) {
          free_kpm_sub_data(&sub);
          continue;
        }
        hndl[i][j] = report_sm_xapp_api(&n->id, KPM_ran_function, &sub, node_cb[i]);
        free_kpm_sub_data(&sub);
      }
    }
  }

  char const* cmd_path = getenv("RC_CMD_FILE");
  char const* ack_path = getenv("RC_ACK_FILE");
  FILE* ack = ack_path != NULL ? fopen(ack_path, "a") : NULL;
  long offset = 0;
  int64_t const t0 = time_now_us();
  while (!stop && (duration_s == 0 || time_now_us() - t0 < (int64_t)duration_s * 1000000)) {
    poll_commands(&nodes, cmd_path, ack, &offset);
    usleep(100000);
  }

  for (size_t i = 0; i < nodes.len; i++) {
    for (size_t j = 0; j < n_hndl[i]; j++)
      if (hndl[i][j].success)
        rm_report_sm_xapp_api(hndl[i][j].u.handle);
    free(hndl[i]);
  }

  while (try_stop_xapp_api() == false)
    usleep(1000);

  free_e2_node_arr_xapp(&nodes);
  if (csv != stdout)
    fclose(csv);
  if (ack != NULL)
    fclose(ack);
  fprintf(stderr, "[ACTUATOR]: done\n");
  return 0;
}
