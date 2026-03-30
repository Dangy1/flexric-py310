//#include "FlexRIC.h"
#include "swig_wrapper.h"

#ifdef XAPP_LANG_PYTHON
#include "Python.h"
#endif

#include "../e42_xapp_api.h"

#include "../../sm/mac_sm/mac_sm_id.h"
#include "../../sm/rlc_sm/rlc_sm_id.h"
#include "../../sm/pdcp_sm/pdcp_sm_id.h"
#include "../../sm/gtp_sm/gtp_sm_id.h"
#include "../../sm/slice_sm/slice_sm_id.h"
#include "../../sm/tc_sm/tc_sm_id.h"
#include "../../sm/rc_sm/rc_sm_id.h"
#include "../../sm/kpm_sm/kpm_sm_id_wrapper.h"
#include "../../util/conf_file.h"

extern "C" {
#include "../../util/time_now_us.h"
}


#include <arpa/inet.h>
#include <cassert>
#include <ctime>
#include <cstdlib>
#include <cstdio>
#include <sstream>
#include <pthread.h>
#include <unistd.h>
#include <iostream>

static
bool initialized = false;


static
const char* convert_period(Interval  inter_arg)
{
  if(inter_arg == Interval::ms_1 ){
    return "1_ms";
  } else if (inter_arg == Interval::ms_2) {
    return "2_ms";
  } else if(inter_arg == Interval::ms_5) {
    return "5_ms";
  } else if(inter_arg == Interval::ms_10) {
    return "10_ms";
  } else {
    assert(0 != 0 && "Unknown type");
  }

}

void init()
{
  assert(initialized == false && "Already initialized!");

  int const argc = 1;
  char** argv = NULL;
  fr_args_t args = init_fr_args(argc, argv);

  initialized = true; 

  init_xapp_api(&args);
}

bool try_stop()
{
  return try_stop_xapp_api();
}

std::vector<E2Node> conn_e2_nodes(void)
{
  e2_node_arr_xapp_t arr = e2_nodes_xapp_api();

  std::vector<E2Node> x; //(arr.len);

  for(int i = 0; i < arr.len; ++i){

    E2Node tmp;

    e2_node_connected_xapp_t const* src = &arr.n[i];
    tmp.id = cp_global_e2_node_id(&src->id); 

    std::vector<ran_function_t> ran_func;//(src->len_rf);

    for(size_t j = 0; j < src->len_rf; ++j){
      ran_function_t rf = {.id = src->rf[j].id, .rev = src->rf[j].rev };
      ran_func.push_back(rf);
    }
    tmp.ran_func = ran_func;
    x.push_back(tmp);//[i] = tmp;
  }

  free_e2_node_arr_xapp(&arr);

  return x;
}

std::vector<int> get_ran_func_ids(E2Node const& node)
{
  std::vector<int> ids;
  ids.reserve(node.ran_func.size());
  for (size_t i = 0; i < node.ran_func.size(); ++i) {
    ids.push_back(node.ran_func[i].id);
  }
  return ids;
}

std::string get_e2_node_id_summary(E2Node const& node)
{
  std::ostringstream os;
  os << "nb_id=" << node.id.nb_id.nb_id
     << ", mcc=" << node.id.plmn.mcc
     << ", mnc=" << node.id.plmn.mnc
     << ", mnc_digit_len=" << node.id.plmn.mnc_digit_len;
  return os.str();
}

static 
mac_cb* hndlr_mac_cb; 

static
void sm_cb_mac(sm_ag_if_rd_t const* rd)
{
  assert(rd != NULL);
  assert(rd->type == INDICATION_MSG_AGENT_IF_ANS_V0);
  assert(rd->ind.type == MAC_STATS_V0);
  assert(hndlr_mac_cb != NULL);

  mac_ind_data_t const* data = &rd->ind.mac; 

  swig_mac_ind_msg_t ind;
  ind.tstamp = data->msg.tstamp;

  for(uint32_t i = 0; i < data->msg.len_ue_stats; ++i){
      mac_ue_stats_impl_t tmp = cp_mac_ue_stats_impl(&data->msg.ue_stats[i]) ;
      ind.ue_stats.emplace_back(tmp);
  }

#ifdef XAPP_LANG_PYTHON
    PyGILState_STATE gstate;
    gstate = PyGILState_Ensure();
#endif

    hndlr_mac_cb->handle(&ind);

#ifdef XAPP_LANG_PYTHON
    PyGILState_Release(gstate);
#endif

}

int report_mac_sm(global_e2_node_id_t* id, Interval inter_arg, mac_cb* handler)
{
  assert(id != NULL);
  assert(handler != NULL);

  hndlr_mac_cb = handler;

  const char* period = convert_period(inter_arg);
  
  sm_ans_xapp_t ans = report_sm_xapp_api(id, SM_MAC_ID, (void*)period, sm_cb_mac);
  assert(ans.success == true); 
  return ans.u.handle;
}


void rm_report_mac_sm(int handle)
{

#ifdef XAPP_LANG_PYTHON
    PyGILState_STATE gstate;
    gstate = PyGILState_Ensure();
#endif

//  assert(hndlr_mac_ans.u.handle != 0);
  rm_report_sm_xapp_api(handle);

#ifdef XAPP_LANG_PYTHON
    PyGILState_Release(gstate);
#endif

}

void control_mac_sm(global_e2_node_id_t* id, mac_ctrl_msg_t* ctrl)
{
  assert(id != NULL);
  assert(ctrl != NULL);

  mac_ctrl_req_data_t cp = {.msg = cp_mac_ctrl_msg(ctrl)};
  control_sm_xapp_api(id, SM_MAC_ID, &cp);
}


//////////////////////////////////////
// RLC SM   
/////////////////////////////////////

//static
//pthread_t t_rlc;

static 
rlc_cb* hndlr_rlc_cb; 

static
void sm_cb_rlc(sm_ag_if_rd_t const* rd)
{
  assert(rd != NULL);
  assert(rd->type == INDICATION_MSG_AGENT_IF_ANS_V0);
  assert(rd->ind.type == RLC_STATS_V0);
  assert(hndlr_rlc_cb != NULL);

  rlc_ind_data_t const* data = &rd->ind.rlc; 

  swig_rlc_ind_msg_t ind;
  ind.tstamp = data->msg.tstamp;

  for(uint32_t i = 0; i < data->msg.len; ++i){
    rlc_radio_bearer_stats_t tmp = data->msg.rb[i];
    ind.rb_stats.push_back(tmp);
  }

#ifdef XAPP_LANG_PYTHON
    PyGILState_STATE gstate;
    gstate = PyGILState_Ensure();
#endif

    hndlr_rlc_cb->handle(&ind);

#ifdef XAPP_LANG_PYTHON
    PyGILState_Release(gstate);
#endif

}

int report_rlc_sm(global_e2_node_id_t* id, Interval inter_arg, rlc_cb* handler)
{

  assert(id != NULL);
  assert(handler != NULL);

  hndlr_rlc_cb = handler;

  const char* period = convert_period(inter_arg);

  sm_ans_xapp_t ans = report_sm_xapp_api(id, SM_RLC_ID, (void*)period, sm_cb_rlc);
  assert(ans.success == true); 
  return ans.u.handle;
}

void rm_report_rlc_sm(int handler)
{

#ifdef XAPP_LANG_PYTHON
    PyGILState_STATE gstate;
    gstate = PyGILState_Ensure();
#endif

  rm_report_sm_xapp_api(handler);

#ifdef XAPP_LANG_PYTHON
    PyGILState_Release(gstate);
#endif

}



//////////////////////////////////////
// PDCP 
/////////////////////////////////////

static 
pdcp_cb* hndlr_pdcp_cb; 

static
void sm_cb_pdcp(sm_ag_if_rd_t const* rd)
{
  assert(rd != NULL);
  assert(rd->type == INDICATION_MSG_AGENT_IF_ANS_V0);
  assert(rd->ind.type == PDCP_STATS_V0);
  assert(hndlr_pdcp_cb != NULL);

  pdcp_ind_data_t const* data = &rd->ind.pdcp; 

  swig_pdcp_ind_msg_t ind;
  ind.tstamp = data->msg.tstamp;

  for(uint32_t i = 0; i < data->msg.len; ++i){
    pdcp_radio_bearer_stats_t tmp = data->msg.rb[i];
    ind.rb_stats.push_back(tmp);
  }

#ifdef XAPP_LANG_PYTHON
    PyGILState_STATE gstate;
    gstate = PyGILState_Ensure();
#endif

    hndlr_pdcp_cb->handle(&ind);

#ifdef XAPP_LANG_PYTHON
    PyGILState_Release(gstate);
#endif

}

int report_pdcp_sm(global_e2_node_id_t* id, Interval inter_arg, pdcp_cb* handler)
{
  assert(id != NULL);
  assert(handler != NULL);

  hndlr_pdcp_cb = handler;

  const char* period = convert_period(inter_arg);
  sm_ans_xapp_t ans = report_sm_xapp_api(id , SM_PDCP_ID, (void*)period, sm_cb_pdcp);
  assert(ans.success == true); 
  return ans.u.handle;
}

void rm_report_pdcp_sm(int handler)
{

#ifdef XAPP_LANG_PYTHON
    PyGILState_STATE gstate;
    gstate = PyGILState_Ensure();
#endif

  rm_report_sm_xapp_api(handler);

#ifdef XAPP_LANG_PYTHON
    PyGILState_Release(gstate);
#endif

}

//////////////////////////////////////
// SLICE Indication & Control
/////////////////////////////////////

static
slice_cb* hndlr_slice_cb;

static
void sm_cb_slice(sm_ag_if_rd_t const* rd)
{
  assert(rd != NULL);
  assert(rd->type == INDICATION_MSG_AGENT_IF_ANS_V0);
  assert(rd->ind.type == SLICE_STATS_V0);
  assert(hndlr_slice_cb != NULL);

  slice_ind_data_t const* data = &rd->ind.slice;

  swig_slice_ind_msg_t ind;
  ind.tstamp = data->msg.tstamp;


  ind.slice_stats.dl.len_slices = data->msg.slice_conf.dl.len_slices;
  ind.slice_stats.dl.sched_name.push_back(data->msg.slice_conf.dl.sched_name);
  for (size_t i = 0; i < ind.slice_stats.dl.len_slices; ++i) {
    swig_fr_slice_t tmp;
    tmp.id = data->msg.slice_conf.dl.slices[i].id;
    tmp.label.push_back(data->msg.slice_conf.dl.slices[i].label);
    tmp.sched.push_back(data->msg.slice_conf.dl.slices[i].sched);
    tmp.params = data->msg.slice_conf.dl.slices[i].params;
    ind.slice_stats.dl.slices.emplace_back(tmp);
  }

  ind.ue_slice_stats.len_ue_slice = data->msg.ue_slice_conf.len_ue_slice;
  for (size_t i = 0; i < ind.ue_slice_stats.len_ue_slice; ++i) {
    ue_slice_assoc_t tmp_ue;
    tmp_ue.rnti = data->msg.ue_slice_conf.ues[i].rnti;
    tmp_ue.dl_id = data->msg.ue_slice_conf.ues[i].dl_id;
    tmp_ue.ul_id = data->msg.ue_slice_conf.ues[i].ul_id;
    ind.ue_slice_stats.ues.emplace_back(tmp_ue);
  }

#ifdef XAPP_LANG_PYTHON
  PyGILState_STATE gstate;
    gstate = PyGILState_Ensure();
#endif

  hndlr_slice_cb->handle(&ind);

#ifdef XAPP_LANG_PYTHON
  PyGILState_Release(gstate);
#endif

}

int report_slice_sm(global_e2_node_id_t* id, Interval inter_arg, slice_cb* handler)
{
  assert( id != NULL);
  (void)inter_arg;
  assert(handler != NULL);

  hndlr_slice_cb = handler;

  const char* period = convert_period(inter_arg);
  sm_ans_xapp_t ans = report_sm_xapp_api(id, SM_SLICE_ID, (void*)period, sm_cb_slice);
  assert(ans.success == true);
  return ans.u.handle;
}

void rm_report_slice_sm(int handler)
{

#ifdef XAPP_LANG_PYTHON
  PyGILState_STATE gstate;
    gstate = PyGILState_Ensure();
#endif

  rm_report_sm_xapp_api(handler);

#ifdef XAPP_LANG_PYTHON
  PyGILState_Release(gstate);
#endif

}

void control_slice_sm(global_e2_node_id_t* id, slice_ctrl_msg_t* ctrl)
{
  assert(id != NULL);
  assert(ctrl != NULL);

  if(ctrl->type == SLICE_CTRL_SM_V0_ADD){
    slice_conf_t* s_conf = &ctrl->u.add_mod_slice;
    assert(s_conf->dl.sched_name != NULL);

    if (s_conf->dl.len_slices == 0)
      std::cout << "RESET DL SLICE, algo = NONE" << '\n';
    for(size_t i =0; i < s_conf->dl.len_slices; ++i) {
      fr_slice_t *s = &s_conf->dl.slices[i];
      assert(s->len_sched != 0);
      assert(s->sched != NULL);
      slice_params_t *p = &s->params;
      if (p->type == SLICE_ALG_SM_V0_STATIC) {
        static_slice_t *sta_sli = &p->u.sta;
        std::cout << "ADD STATIC DL SLICE: id " << s->id <<
                  ", label " << s->label <<
                  ", pos_low " << sta_sli->pos_low <<
                  ", pos_high " << sta_sli->pos_high << '\n';
      } else if (p->type == SLICE_ALG_SM_V0_NVS) {
        nvs_slice_t *nvs_sli = &p->u.nvs;
        if (nvs_sli->conf == SLICE_SM_NVS_V0_RATE)
          std::cout << "ADD NVS DL SLICE: id " << s->id <<
                    ", label " << s->label <<
                    ", conf " << nvs_sli->conf << "(rate)" <<
                    ", mbps_required " << nvs_sli->u.rate.u1.mbps_required <<
                    ", mbps_reference " << nvs_sli->u.rate.u2.mbps_reference << '\n';
        else if (nvs_sli->conf == SLICE_SM_NVS_V0_CAPACITY)
          std::cout << "ADD NVS DL SLICE: id " << s->id <<
                    ", label " << s->label <<
                    ", conf " << nvs_sli->conf << "(capacity)" <<
                    ", pct_reserved " << nvs_sli->u.capacity.u.pct_reserved << '\n';
        else assert(0 != 0 && "Unknow NVS conf");
      } else if (p->type == SLICE_ALG_SM_V0_EDF) {
        edf_slice_t *edf_sli = &p->u.edf;
        std::cout << "ADD EDF DL SLICE: id " << s->id <<
                  ", label " << s->label <<
                  ", deadline " << edf_sli->deadline <<
                  ", guaranteed_prbs " << edf_sli->guaranteed_prbs <<
                  ", max_replenish " << edf_sli->max_replenish << '\n';
      } else assert(0 != 0 && "Unknow slice algo type");
    }
  } else if(ctrl->type == SLICE_CTRL_SM_V0_UE_SLICE_ASSOC){
    for (size_t i = 0; i <  ctrl->u.ue_slice.len_ue_slice; ++i)
      std::cout << "ASSOC DL SLICE: rnti " << std::hex << ctrl->u.ue_slice.ues[i].rnti <<
                ", to slice id " << ctrl->u.ue_slice.ues[i].dl_id << '\n';
  } else if (ctrl->type == SLICE_CTRL_SM_V0_DEL) {
    del_slice_conf_t* d_conf = &ctrl->u.del_slice;
    for (size_t i = 0; i <  d_conf->len_dl; ++i)
      std::cout << "DEL DL SLICE: id " << d_conf->dl[i] << '\n';
    // TODO: UL

  } else {
    assert(0!=0 && "not foreseen case");
  }

  //sm_ag_if_wr_t wr;
  //wr.type = CONTROL_SM_AG_IF_WR;
  //wr.ctrl.type = SLICE_CTRL_REQ_V0;
  //wr.ctrl.slice_req_ctrl.msg = 
  slice_ctrl_req_data_t cp = {.msg = cp_slice_ctrl_msg(ctrl)};  
  control_sm_xapp_api(id, SM_SLICE_ID, &cp);
}

//////////////////////////////////////
// TC SM
/////////////////////////////////////

static
tc_cb* hndlr_tc_cb;

static
void sm_cb_tc(sm_ag_if_rd_t const* rd)
{
  assert(rd != NULL);
  assert(rd->type == INDICATION_MSG_AGENT_IF_ANS_V0);
  assert(rd->ind.type == TC_STATS_V0);
  assert(hndlr_tc_cb != NULL);

  tc_ind_data_t ind = cp_tc_ind_data(&rd->ind.tc);

#ifdef XAPP_LANG_PYTHON
    PyGILState_STATE gstate;
    gstate = PyGILState_Ensure();
#endif

  hndlr_tc_cb->handle(&ind);

#ifdef XAPP_LANG_PYTHON
    PyGILState_Release(gstate);
#endif

  free_tc_ind_data(&ind);
}

int report_tc_sm(global_e2_node_id_t* id, Interval inter_arg, tc_cb* handler)
{
  assert(id != NULL);
  assert(handler != NULL);

  hndlr_tc_cb = handler;

  const char* period = convert_period(inter_arg);
  sm_ans_xapp_t ans = report_sm_xapp_api(id, SM_TC_ID, (void*)period, sm_cb_tc);
  assert(ans.success == true);
  return ans.u.handle;
}

void rm_report_tc_sm(int handler)
{

#ifdef XAPP_LANG_PYTHON
    PyGILState_STATE gstate;
    gstate = PyGILState_Ensure();
#endif

  rm_report_sm_xapp_api(handler);

#ifdef XAPP_LANG_PYTHON
    PyGILState_Release(gstate);
#endif
}

void control_tc_sm(global_e2_node_id_t* id, tc_ctrl_msg_t* ctrl)
{
  assert(id != NULL);
  assert(ctrl != NULL);

  tc_ctrl_req_data_t cp = {.msg = cp_tc_ctrl_msg(ctrl)};
  control_sm_xapp_api(id, SM_TC_ID, &cp);
}

tc_ctrl_msg_t tc_gen_mod_bdp_pcr(uint32_t drb_sz, int64_t tstamp)
{
  tc_ctrl_msg_t ans{};
  ans.type = TC_CTRL_SM_V0_PCR;
  ans.pcr.act = TC_CTRL_ACTION_SM_V0_MOD;
  ans.pcr.mod.type = TC_PCR_5G_BDP;
  ans.pcr.mod.bdp.drb_sz = drb_sz;
  ans.pcr.mod.bdp.tstamp = tstamp;
  return ans;
}

tc_ctrl_msg_t tc_gen_add_codel_queue(uint32_t interval_ms, uint32_t target_ms)
{
  tc_ctrl_msg_t ans{};
  ans.type = TC_CTRL_SM_V0_QUEUE;
  ans.q.act = TC_CTRL_ACTION_SM_V0_ADD;
  ans.q.add.type = TC_QUEUE_CODEL;
  ans.q.add.codel.interval_ms = interval_ms;
  ans.q.add.codel.target_ms = target_ms;
  return ans;
}

tc_ctrl_msg_t tc_gen_add_ecn_queue(uint32_t interval_ms, uint32_t target_ms)
{
  tc_ctrl_msg_t ans{};
  ans.type = TC_CTRL_SM_V0_QUEUE;
  ans.q.act = TC_CTRL_ACTION_SM_V0_ADD;
  ans.q.add.type = TC_QUEUE_ECN_CODEL;
  ans.q.add.ecn.interval_ms = interval_ms;
  ans.q.add.ecn.target_ms = target_ms;
  return ans;
}

tc_ctrl_msg_t tc_gen_add_fifo_queue(void)
{
  tc_ctrl_msg_t ans{};
  ans.type = TC_CTRL_SM_V0_QUEUE;
  ans.q.act = TC_CTRL_ACTION_SM_V0_ADD;
  ans.q.add.type = TC_QUEUE_FIFO;
  return ans;
}

tc_ctrl_msg_t tc_gen_add_osi_cls(int32_t src_port, int32_t dst_port, int32_t protocol, int32_t src_addr, int32_t dst_addr, uint32_t dst_queue)
{
  tc_ctrl_msg_t ans{};
  ans.type = TC_CTRL_SM_V0_CLS;
  ans.cls.act = TC_CTRL_ACTION_SM_V0_ADD;
  ans.cls.add.type = TC_CLS_OSI;
  ans.cls.add.osi.dst_queue = dst_queue;
  ans.cls.add.osi.l3.src_addr = src_addr;
  ans.cls.add.osi.l3.dst_addr = dst_addr;
  ans.cls.add.osi.l4.src_port = src_port;
  ans.cls.add.osi.l4.dst_port = dst_port;
  ans.cls.add.osi.l4.protocol = protocol;
  return ans;
}

tc_ctrl_msg_t tc_gen_mod_shaper(uint32_t shaper_id, uint32_t time_window_ms, uint32_t max_rate_kbps, uint32_t active)
{
  tc_ctrl_msg_t ans{};
  ans.type = TC_CTRL_SM_V0_SHP;
  ans.shp.act = TC_CTRL_ACTION_SM_V0_MOD;
  ans.shp.mod.id = shaper_id;
  ans.shp.mod.time_window_ms = time_window_ms;
  ans.shp.mod.max_rate_kbps = max_rate_kbps;
  ans.shp.mod.active = active;
  return ans;
}

//////////////////////////////////////
// GTP SM   
/////////////////////////////////////

static 
gtp_cb* hndlr_gtp_cb; 

static
void sm_cb_gtp(sm_ag_if_rd_t const* rd)
{
  assert(rd != NULL);
  assert(rd->type == INDICATION_MSG_AGENT_IF_ANS_V0);
  assert(rd->ind.type == GTP_STATS_V0);
  assert(hndlr_gtp_cb != NULL);

  gtp_ind_data_t const* data = &rd->ind.gtp; 

  swig_gtp_ind_msg_t ind;
  ind.tstamp = data->msg.tstamp;

  for(uint32_t i = 0; i < data->msg.len; ++i){
    gtp_ngu_t_stats_t tmp = data->msg.ngut[i];
    ind.gtp_stats.push_back(tmp);
  }

#ifdef XAPP_LANG_PYTHON
    PyGILState_STATE gstate;
    gstate = PyGILState_Ensure();
#endif

    hndlr_gtp_cb->handle(&ind);

#ifdef XAPP_LANG_PYTHON
    PyGILState_Release(gstate);
#endif

}

int report_gtp_sm(global_e2_node_id_t* id, Interval inter_arg, gtp_cb* handler)
{
  assert(id != NULL);
  assert(handler != NULL);

  hndlr_gtp_cb = handler;

  const char* period = convert_period(inter_arg);
  sm_ans_xapp_t ans = report_sm_xapp_api(id, SM_GTP_ID, (void*)period, sm_cb_gtp);
  assert(ans.success == true); 
  return ans.u.handle;
}

void rm_report_gtp_sm(int handler)
{

#ifdef XAPP_LANG_PYTHON
    PyGILState_STATE gstate;
    gstate = PyGILState_Ensure();
#endif

  rm_report_sm_xapp_api(handler);

#ifdef XAPP_LANG_PYTHON
    PyGILState_Release(gstate);
#endif

}

//////////////////////////////////////
// KPM SM
/////////////////////////////////////

static
kpm_cb* hndlr_kpm_cb;

static
kpm_moni_cb* hndlr_kpm_moni_cb;

static
uint64_t kpm_period_ms = 1000;

static
pthread_mutex_t kpm_log_mtx = PTHREAD_MUTEX_INITIALIZER;

static
test_info_lst_t kpm_filter_predicate(test_cond_type_e type, test_cond_e cond, int value)
{
  test_info_lst_t dst{};
  dst.test_cond_type = type;
  dst.S_NSSAI = TRUE_TEST_COND_TYPE;

  dst.test_cond = (test_cond_e*)calloc(1, sizeof(test_cond_e));
  assert(dst.test_cond != NULL);
  *dst.test_cond = cond;

  dst.test_cond_value = (test_cond_value_t*)calloc(1, sizeof(test_cond_value_t));
  assert(dst.test_cond_value != NULL);
  dst.test_cond_value->type = OCTET_STRING_TEST_COND_VALUE;

  dst.test_cond_value->octet_string_value = (byte_array_t*)calloc(1, sizeof(byte_array_t));
  assert(dst.test_cond_value->octet_string_value != NULL);
  dst.test_cond_value->octet_string_value->len = 1;
  dst.test_cond_value->octet_string_value->buf = (uint8_t*)calloc(1, sizeof(uint8_t));
  assert(dst.test_cond_value->octet_string_value->buf != NULL);
  dst.test_cond_value->octet_string_value->buf[0] = value;

  return dst;
}

static
label_info_lst_t kpm_fill_label()
{
  label_info_lst_t label = {0};
  label.noLabel = (enum_value_e*)calloc(1, sizeof(enum_value_e));
  assert(label.noLabel != NULL);
  *label.noLabel = TRUE_ENUM_VALUE;
  return label;
}

static
kpm_act_def_format_1_t kpm_fill_act_def_frm_1(ric_report_style_item_t const* report_item)
{
  assert(report_item != NULL);
  kpm_act_def_format_1_t ad{};
  ad.meas_info_lst_len = report_item->meas_info_for_action_lst_len;
  ad.meas_info_lst = (meas_info_format_1_lst_t*)calloc(ad.meas_info_lst_len, sizeof(meas_info_format_1_lst_t));
  assert(ad.meas_info_lst != NULL);

  for (size_t i = 0; i < ad.meas_info_lst_len; ++i) {
    meas_info_format_1_lst_t* meas = &ad.meas_info_lst[i];
    meas->meas_type.type = meas_type_t::NAME_MEAS_TYPE;
    meas->meas_type.name = copy_byte_array(report_item->meas_info_for_action_lst[i].name);
    meas->label_info_lst_len = 1;
    meas->label_info_lst = (label_info_lst_t*)calloc(1, sizeof(label_info_lst_t));
    assert(meas->label_info_lst != NULL);
    meas->label_info_lst[0] = kpm_fill_label();
  }

  ad.gran_period_ms = kpm_period_ms;
  ad.cell_global_id = NULL;
#if defined KPM_V2_03 || defined KPM_V3_00
  ad.meas_bin_range_info_lst_len = 0;
  ad.meas_bin_info_lst = NULL;
#endif
  return ad;
}

static
kpm_act_def_t kpm_fill_format_1(ric_report_style_item_t const* report_item)
{
  kpm_act_def_t act_def = {.type = FORMAT_1_ACTION_DEFINITION};
  act_def.frm_1 = kpm_fill_act_def_frm_1(report_item);
  return act_def;
}

static
kpm_act_def_t kpm_fill_format_4(ric_report_style_item_t const* report_item)
{
  kpm_act_def_t act_def = {.type = FORMAT_4_ACTION_DEFINITION};
  act_def.frm_4.matching_cond_lst_len = 1;
  act_def.frm_4.matching_cond_lst = (matching_condition_format_4_lst_t*)calloc(1, sizeof(matching_condition_format_4_lst_t));
  assert(act_def.frm_4.matching_cond_lst != NULL);
  act_def.frm_4.matching_cond_lst[0].test_info_lst =
      kpm_filter_predicate(S_NSSAI_TEST_COND_TYPE, EQUAL_TEST_COND, 1);
  act_def.frm_4.action_def_format_1 = kpm_fill_act_def_frm_1(report_item);
  return act_def;
}

static
bool kpm_build_subscription(kpm_ran_function_def_t const* ran_func, uint64_t period_ms, kpm_sub_data_t* out)
{
  assert(ran_func != NULL);
  assert(out != NULL);

  if (ran_func->sz_ric_event_trigger_style_list == 0 || ran_func->ric_event_trigger_style_list == NULL) {
    return false;
  }

  bool trg_ok = false;
  for (size_t i = 0; i < ran_func->sz_ric_event_trigger_style_list; ++i) {
    if (ran_func->ric_event_trigger_style_list[i].format_type == FORMAT_1_RIC_EVENT_TRIGGER) {
      trg_ok = true;
      break;
    }
  }
  if (trg_ok == false) {
    return false;
  }

  if (ran_func->sz_ric_report_style_list == 0 || ran_func->ric_report_style_list == NULL) {
    return false;
  }

  size_t rep_idx = ran_func->sz_ric_report_style_list;
  for (size_t i = 0; i < ran_func->sz_ric_report_style_list; ++i) {
    ric_report_style_item_t const* item = &ran_func->ric_report_style_list[i];
    if (item->meas_info_for_action_lst_len == 0 || item->meas_info_for_action_lst == NULL) {
      continue;
    }
    if (item->act_def_format_type == FORMAT_4_ACTION_DEFINITION) {
      rep_idx = i;
      break;
    }
    if (item->act_def_format_type == FORMAT_1_ACTION_DEFINITION && rep_idx == ran_func->sz_ric_report_style_list) {
      rep_idx = i;
    }
  }
  if (rep_idx == ran_func->sz_ric_report_style_list) {
    return false;
  }

  kpm_period_ms = period_ms;
  out->ev_trg_def.type = FORMAT_1_RIC_EVENT_TRIGGER;
  out->ev_trg_def.kpm_ric_event_trigger_format_1.report_period_ms = period_ms;

  out->sz_ad = 1;
  out->ad = (kpm_act_def_t*)calloc(1, sizeof(kpm_act_def_t));
  assert(out->ad != NULL);

  ric_report_style_item_t const* report_item = &ran_func->ric_report_style_list[rep_idx];
  if (report_item->act_def_format_type == FORMAT_4_ACTION_DEFINITION) {
    out->ad[0] = kpm_fill_format_4(report_item);
  } else {
    out->ad[0] = kpm_fill_format_1(report_item);
  }

  return true;
}

static
bool kpm_find_node_sub(global_e2_node_id_t const* id, uint64_t period_ms, kpm_sub_data_t* out_sub)
{
  assert(id != NULL);
  assert(out_sub != NULL);

  e2_node_arr_xapp_t arr = e2_nodes_xapp_api();
  bool found = false;

  for (size_t i = 0; i < arr.len && found == false; ++i) {
    e2_node_connected_xapp_t const* n = &arr.n[i];
    if (eq_global_e2_node_id(id, &n->id) == false) {
      continue;
    }

    for (size_t j = 0; j < n->len_rf; ++j) {
      sm_ran_function_t const* rf = &n->rf[j];
      if (rf->id != SM_KPM_ID || rf->defn.type != KPM_RAN_FUNC_DEF_E) {
        continue;
      }
      found = kpm_build_subscription(&rf->defn.kpm, period_ms, out_sub);
      break;
    }
  }

  free_e2_node_arr_xapp(&arr);
  return found;
}

static
void kpm_print_ue_id(ue_id_e2sm_t const* ue_id)
{
  assert(ue_id != NULL);
  switch (ue_id->type) {
    case GNB_UE_ID_E2SM:
      if (ue_id->gnb.gnb_cu_ue_f1ap_lst != NULL && ue_id->gnb.gnb_cu_ue_f1ap_lst_len > 0) {
        printf("UE type=gNB-CU gnb_cu_ue_f1ap=%u\n", ue_id->gnb.gnb_cu_ue_f1ap_lst[0]);
      } else {
        printf("UE type=gNB amf_ue_ngap_id=%lu\n", ue_id->gnb.amf_ue_ngap_id);
      }
      if (ue_id->gnb.ran_ue_id != NULL) {
        printf("ran_ue_id=%lx\n", *ue_id->gnb.ran_ue_id);
      }
      break;
    case GNB_DU_UE_ID_E2SM:
      printf("UE type=gNB-DU gnb_cu_ue_f1ap=%u\n", ue_id->gnb_du.gnb_cu_ue_f1ap);
      if (ue_id->gnb_du.ran_ue_id != NULL) {
        printf("ran_ue_id=%lx\n", *ue_id->gnb_du.ran_ue_id);
      }
      break;
    case GNB_CU_UP_UE_ID_E2SM:
      printf("UE type=gNB-CU-UP gnb_cu_cp_ue_e1ap=%u\n", ue_id->gnb_cu_up.gnb_cu_cp_ue_e1ap);
      if (ue_id->gnb_cu_up.ran_ue_id != NULL) {
        printf("ran_ue_id=%lx\n", *ue_id->gnb_cu_up.ran_ue_id);
      }
      break;
    default:
      printf("UE type=%d\n", ue_id->type);
      break;
  }
}

static
void kpm_print_meas_value(meas_type_t const* meas_type, meas_record_lst_t const* rec)
{
  if (meas_type == NULL || rec == NULL) {
    return;
  }

  if (meas_type->type == meas_type_t::NAME_MEAS_TYPE) {
    printf("%.*s = ", (int)meas_type->name.len, (char const*)meas_type->name.buf);
  } else {
    printf("meas_id_%u = ", meas_type->id);
  }

  switch (rec->value) {
    case INTEGER_MEAS_VALUE:
      printf("%u\n", rec->int_val);
      break;
    case REAL_MEAS_VALUE:
      printf("%.3f\n", rec->real_val);
      break;
    case NO_VALUE_MEAS_VALUE:
    default:
      printf("N/A\n");
      break;
  }
}

static
bool kpm_build_one_record_line(std::string const& prefix,
                               kpm_ind_msg_format_1_t const* frm1,
                               std::string* out)
{
  if (frm1 == NULL || out == NULL) {
    return false;
  }
  if (frm1->meas_data_lst_len == 0 || frm1->meas_info_lst_len == 0) {
    return false;
  }

  meas_data_lst_t const* data = &frm1->meas_data_lst[0];
  if (data->meas_record_len == 0) {
    return false;
  }

  size_t idx = 0;
  if (idx >= frm1->meas_info_lst_len) {
    idx = frm1->meas_info_lst_len - 1;
  }
  if (idx >= data->meas_record_len) {
    idx = data->meas_record_len - 1;
  }

  std::ostringstream line;
  line << prefix;
  meas_type_t const* mt = &frm1->meas_info_lst[idx].meas_type;
  if (mt->type == meas_type_t::NAME_MEAS_TYPE) {
    line << "meas=" << std::string((char const*)mt->name.buf, mt->name.len) << " ";
  } else {
    line << "meas_id=" << mt->id << " ";
  }

  meas_record_lst_t const* rec = &data->meas_record_lst[idx];
  if (rec->value == INTEGER_MEAS_VALUE) {
    line << "value=" << rec->int_val;
  } else if (rec->value == REAL_MEAS_VALUE) {
    line << "value=" << rec->real_val;
  } else {
    line << "value=N/A";
  }

  *out = line.str();
  return true;
}

static
std::string kpm_ue_prefix(ue_id_e2sm_t const* ue_id)
{
  assert(ue_id != NULL);
  std::ostringstream os;
  switch (ue_id->type) {
    case GNB_UE_ID_E2SM:
      os << "ue_type=gnb ";
      if (ue_id->gnb.ran_ue_id != NULL) {
        os << "ran_ue_id=0x" << std::hex << *ue_id->gnb.ran_ue_id << std::dec << " ";
      } else {
        os << "amf_ue_ngap_id=" << ue_id->gnb.amf_ue_ngap_id << " ";
      }
      break;
    case GNB_DU_UE_ID_E2SM:
      os << "ue_type=gnb_du gnb_cu_ue_f1ap=" << ue_id->gnb_du.gnb_cu_ue_f1ap << " ";
      break;
    case GNB_CU_UP_UE_ID_E2SM:
      os << "ue_type=gnb_cu_up gnb_cu_cp_ue_e1ap=" << ue_id->gnb_cu_up.gnb_cu_cp_ue_e1ap << " ";
      break;
    default:
      os << "ue_type=" << ue_id->type << " ";
      break;
  }
  return os.str();
}

static
void sm_cb_kpm_py(sm_ag_if_rd_t const* rd)
{
  assert(rd != NULL);
  assert(rd->type == INDICATION_MSG_AGENT_IF_ANS_V0);
  assert(rd->ind.type == KPM_STATS_V3_0);
  assert(hndlr_kpm_moni_cb != NULL);

  kpm_ind_data_t const* ind = &rd->ind.kpm.ind;
  swig_kpm_ind_msg_t out{};
  out.tstamp = ind->hdr.kpm_ric_ind_hdr_format_1.collectStartTime;

  if (ind->msg.type == FORMAT_3_INDICATION_MESSAGE) {
    kpm_ind_msg_format_3_t const* msg = &ind->msg.frm_3;
    for (size_t i = 0; i < msg->ue_meas_report_lst_len; ++i) {
      meas_report_per_ue_t const* per_ue = &msg->meas_report_per_ue[i];
      std::string const prefix = kpm_ue_prefix(&per_ue->ue_meas_report_lst);
      kpm_ind_msg_format_1_t const* frm1 = &per_ue->ind_msg_format_1;

      for (size_t j = 0; j < frm1->meas_data_lst_len; ++j) {
        meas_data_lst_t const* data = &frm1->meas_data_lst[j];
        for (size_t k = 0; k < data->meas_record_len && k < frm1->meas_info_lst_len; ++k) {
          std::ostringstream line;
          line << prefix;
          meas_type_t const* mt = &frm1->meas_info_lst[k].meas_type;
          if (mt->type == meas_type_t::NAME_MEAS_TYPE) {
            line << "meas=" << std::string((char const*)mt->name.buf, mt->name.len) << " ";
          } else {
            line << "meas_id=" << mt->id << " ";
          }

          meas_record_lst_t const* rec = &data->meas_record_lst[k];
          if (rec->value == INTEGER_MEAS_VALUE) {
            line << "value=" << rec->int_val;
          } else if (rec->value == REAL_MEAS_VALUE) {
            line << "value=" << rec->real_val;
          } else {
            line << "value=N/A";
          }
          out.records.emplace_back(line.str());
        }
      }
    }
  } else if (ind->msg.type == FORMAT_1_INDICATION_MESSAGE) {
    kpm_ind_msg_format_1_t const* frm1 = &ind->msg.frm_1;
    for (size_t j = 0; j < frm1->meas_data_lst_len; ++j) {
      meas_data_lst_t const* data = &frm1->meas_data_lst[j];
      for (size_t k = 0; k < data->meas_record_len && k < frm1->meas_info_lst_len; ++k) {
        std::ostringstream line;
        line << "ue_type=node ";
        meas_type_t const* mt = &frm1->meas_info_lst[k].meas_type;
        if (mt->type == meas_type_t::NAME_MEAS_TYPE) {
          line << "meas=" << std::string((char const*)mt->name.buf, mt->name.len) << " ";
        } else {
          line << "meas_id=" << mt->id << " ";
        }

        meas_record_lst_t const* rec = &data->meas_record_lst[k];
        if (rec->value == INTEGER_MEAS_VALUE) {
          line << "value=" << rec->int_val;
        } else if (rec->value == REAL_MEAS_VALUE) {
          line << "value=" << rec->real_val;
        } else {
          line << "value=N/A";
        }
        out.records.emplace_back(line.str());
      }
    }
  }

#ifdef XAPP_LANG_PYTHON
  PyGILState_STATE gstate;
  gstate = PyGILState_Ensure();
#endif

  hndlr_kpm_moni_cb->handle(&out);

#ifdef XAPP_LANG_PYTHON
  PyGILState_Release(gstate);
#endif
}

static
void sm_cb_kpm(sm_ag_if_rd_t const* rd)
{
  assert(rd != NULL);
  assert(rd->type == INDICATION_MSG_AGENT_IF_ANS_V0);
  assert(rd->ind.type == KPM_STATS_V3_0);
  assert(hndlr_kpm_cb != NULL);

  kpm_ind_data_t ind = cp_kpm_ind_data(&rd->ind.kpm.ind);

#ifdef XAPP_LANG_PYTHON
    PyGILState_STATE gstate;
    gstate = PyGILState_Ensure();
#endif

  hndlr_kpm_cb->handle(&ind);

#ifdef XAPP_LANG_PYTHON
    PyGILState_Release(gstate);
#endif

  free_kpm_ind_data(&ind);
}

static
void sm_cb_kpm_moni(sm_ag_if_rd_t const* rd)
{
  assert(rd != NULL);
  assert(rd->type == INDICATION_MSG_AGENT_IF_ANS_V0);
  assert(rd->ind.type == KPM_STATS_V3_0);

  kpm_ind_data_t const* ind = &rd->ind.kpm.ind;
  kpm_ric_ind_hdr_format_1_t const* hdr = &ind->hdr.kpm_ric_ind_hdr_format_1;
  int64_t const now = time_now_us();

  pthread_mutex_lock(&kpm_log_mtx);
  printf("\nKPM latency = %ld [us]\n", now - hdr->collectStartTime);
  if (ind->msg.type == FORMAT_3_INDICATION_MESSAGE) {
    kpm_ind_msg_format_3_t const* msg = &ind->msg.frm_3;
    for (size_t i = 0; i < msg->ue_meas_report_lst_len; ++i) {
      meas_report_per_ue_t const* per_ue = &msg->meas_report_per_ue[i];
      kpm_print_ue_id(&per_ue->ue_meas_report_lst);
      std::string one;
      if (kpm_build_one_record_line("", &per_ue->ind_msg_format_1, &one) == true) {
        printf("%s\n", one.c_str());
      }
    }
  } else if (ind->msg.type == FORMAT_1_INDICATION_MESSAGE) {
    std::string one;
    if (kpm_build_one_record_line("", &ind->msg.frm_1, &one) == true) {
      printf("%s\n", one.c_str());
    }
  }
  pthread_mutex_unlock(&kpm_log_mtx);
}

int report_kpm_sm(global_e2_node_id_t* id, kpm_sub_data_t* sub, kpm_cb* handler)
{
  assert(id != NULL);
  assert(sub != NULL);
  assert(handler != NULL);

  hndlr_kpm_cb = handler;
  sm_ans_xapp_t ans = report_sm_xapp_api(id, SM_KPM_ID, sub, sm_cb_kpm);
  assert(ans.success == true);
  return ans.u.handle;
}

int report_kpm_sm_auto(global_e2_node_id_t* id, uint64_t period_ms, kpm_cb* handler)
{
  assert(id != NULL);
  assert(handler != NULL);

  kpm_sub_data_t sub{};
  bool const ok = kpm_find_node_sub(id, period_ms, &sub);
  if (ok == false) {
    return -1;
  }

  hndlr_kpm_cb = handler;
  sm_ans_xapp_t ans = report_sm_xapp_api(id, SM_KPM_ID, &sub, sm_cb_kpm);
  free_kpm_sub_data(&sub);
  if (ans.success == false) {
    return -1;
  }
  return ans.u.handle;
}

int report_kpm_sm_auto_moni(global_e2_node_id_t* id, uint64_t period_ms)
{
  assert(id != NULL);

  kpm_sub_data_t sub{};
  bool const ok = kpm_find_node_sub(id, period_ms, &sub);
  if (ok == false) {
    return -1;
  }

  sm_ans_xapp_t ans = report_sm_xapp_api(id, SM_KPM_ID, &sub, sm_cb_kpm_moni);
  free_kpm_sub_data(&sub);
  if (ans.success == false) {
    return -1;
  }
  return ans.u.handle;
}

int report_kpm_sm_auto_py(global_e2_node_id_t* id, uint64_t period_ms, kpm_moni_cb* handler)
{
  assert(id != NULL);
  assert(handler != NULL);

  kpm_sub_data_t sub{};
  bool const ok = kpm_find_node_sub(id, period_ms, &sub);
  if (ok == false) {
    return -1;
  }

  hndlr_kpm_moni_cb = handler;
  sm_ans_xapp_t ans = report_sm_xapp_api(id, SM_KPM_ID, &sub, sm_cb_kpm_py);
  free_kpm_sub_data(&sub);
  if (ans.success == false) {
    return -1;
  }
  return ans.u.handle;
}

void rm_report_kpm_sm(int handler)
{

#ifdef XAPP_LANG_PYTHON
    PyGILState_STATE gstate;
    gstate = PyGILState_Ensure();
#endif

  rm_report_sm_xapp_api(handler);

#ifdef XAPP_LANG_PYTHON
    PyGILState_Release(gstate);
#endif
}

//////////////////////////////////////
// RC SM
/////////////////////////////////////

static
rc_cb* hndlr_rc_cb;

static
void sm_cb_rc(sm_ag_if_rd_t const* rd)
{
  assert(rd != NULL);
  assert(rd->type == INDICATION_MSG_AGENT_IF_ANS_V0);
  assert(rd->ind.type == RAN_CTRL_STATS_V1_03);
  assert(hndlr_rc_cb != NULL);

  rc_ind_data_t ind = cp_rc_ind_data(&rd->ind.rc.ind);

#ifdef XAPP_LANG_PYTHON
    PyGILState_STATE gstate;
    gstate = PyGILState_Ensure();
#endif

  hndlr_rc_cb->handle(&ind);

#ifdef XAPP_LANG_PYTHON
    PyGILState_Release(gstate);
#endif

  free_rc_ind_data(&ind);
}

int report_rc_sm(global_e2_node_id_t* id, rc_sub_data_t* sub, rc_cb* handler)
{
  assert(id != NULL);
  assert(sub != NULL);
  assert(handler != NULL);

  hndlr_rc_cb = handler;
  sm_ans_xapp_t ans = report_sm_xapp_api(id, SM_RC_ID, sub, sm_cb_rc);
  assert(ans.success == true);
  return ans.u.handle;
}

void rm_report_rc_sm(int handler)
{

#ifdef XAPP_LANG_PYTHON
    PyGILState_STATE gstate;
    gstate = PyGILState_Ensure();
#endif

  rm_report_sm_xapp_api(handler);

#ifdef XAPP_LANG_PYTHON
    PyGILState_Release(gstate);
#endif
}

void control_rc_sm(global_e2_node_id_t* id, rc_ctrl_req_data_t* ctrl)
{
  assert(id != NULL);
  assert(ctrl != NULL);

  control_sm_xapp_api(id, SM_RC_ID, ctrl);
}
