#ifndef SWIG_WRAPPER_H
#define SWIG_WRAPPER_H 

#include <cstddef>
#include <memory>
#include <string>
#include <vector>

#include "../../lib/e2ap/e2ap_global_node_id_wrapper.h"
#include "../../lib/e2ap/e2ap_plmn_wrapper.h"
#include "../../lib/e2ap/e2ap_ran_function_wrapper.h"

#include "../../sm/mac_sm/ie/mac_data_ie.h"
#include "../../sm/rlc_sm/ie/rlc_data_ie.h"
#include "../../sm/pdcp_sm/ie/pdcp_data_ie.h"
#include "../../sm/slice_sm/ie/slice_data_ie.h"
#include "../../sm/tc_sm/ie/tc_data_ie.h"
#include "../../sm/gtp_sm/ie/gtp_data_ie.h"
#include "../../sm/rc_sm/ie/rc_data_ie.h"
#include "../../sm/kpm_sm/kpm_data_ie_wrapper.h"

//////////////////////////////////////
// General    
/////////////////////////////////////

struct E2Node {
  global_e2_node_id_t id;
  std::vector<ran_function_t> ran_func;
};

std::vector<int> get_ran_func_ids(E2Node const& node);
std::string get_e2_node_id_summary(E2Node const& node);

void init(void); 

bool try_stop(void);

std::vector<E2Node> conn_e2_nodes(void);

enum class Interval {
  ms_1,
  ms_2,
  ms_5,
  ms_10,
};

//////////////////////////////////////
// MAC SM   
/////////////////////////////////////

struct swig_mac_ind_msg_t{
  std::vector<mac_ue_stats_impl_t> ue_stats;
  int64_t tstamp;
};

struct mac_cb {
    virtual void handle(swig_mac_ind_msg_t* a) = 0;
    virtual ~mac_cb() {}
};

int report_mac_sm(global_e2_node_id_t* id, Interval inter, mac_cb* handler);

void rm_report_mac_sm(int);

void control_mac_sm(global_e2_node_id_t* id, mac_ctrl_msg_t* ctrl);

//////////////////////////////////////
// RLC SM   
/////////////////////////////////////

struct swig_rlc_ind_msg_t{
  std::vector<rlc_radio_bearer_stats_t> rb_stats; 
  int64_t tstamp;
};

struct rlc_cb {
    virtual void handle(swig_rlc_ind_msg_t* a) = 0;
    virtual ~rlc_cb() {}
};

int report_rlc_sm(global_e2_node_id_t* id, Interval inter, rlc_cb* handler);

void rm_report_rlc_sm(int);

//////////////////////////////////////
// PDCP SM   
/////////////////////////////////////

struct swig_pdcp_ind_msg_t{
  std::vector<pdcp_radio_bearer_stats_t> rb_stats;
  int64_t tstamp;
};

struct pdcp_cb {
    virtual void handle(swig_pdcp_ind_msg_t* a) = 0;
    virtual ~pdcp_cb() {}
};

int report_pdcp_sm(global_e2_node_id_t* id, Interval inter, pdcp_cb* handler);

void rm_report_pdcp_sm(int);

//////////////////////////////////////
// SLICE SM   
/////////////////////////////////////

typedef struct{
    uint32_t id;

    uint32_t len_label;
    std::vector<std::string> label;

    uint32_t len_sched;
    std::vector<std::string> sched;

    slice_params_t params;
} swig_fr_slice_t ;

typedef struct{
    uint32_t len_slices;
    std::vector<swig_fr_slice_t> slices;

    uint32_t len_sched_name;
    std::vector<std::string> sched_name;
} swig_ul_dl_slice_conf_t ;

typedef struct{
    swig_ul_dl_slice_conf_t dl;
    swig_ul_dl_slice_conf_t ul;
} swig_slice_conf_t ;

typedef struct{
    uint32_t len_ue_slice;
    std::vector<ue_slice_assoc_t> ues;
} swig_ue_slice_conf_t;

struct swig_slice_ind_msg_t{
  swig_slice_conf_t slice_stats;
  swig_ue_slice_conf_t ue_slice_stats;
  int64_t tstamp;
};

struct slice_cb {
    virtual void handle(swig_slice_ind_msg_t* a) = 0;
    virtual ~slice_cb() {}
};

int report_slice_sm(global_e2_node_id_t* id, Interval inter, slice_cb* handler);

void rm_report_slice_sm(int);

void control_slice_sm(global_e2_node_id_t* id, slice_ctrl_msg_t* ctrl);

//////////////////////////////////////
// TC SM
/////////////////////////////////////

struct tc_cb {
    virtual void handle(tc_ind_data_t* a) = 0;
    virtual ~tc_cb() {}
};

int report_tc_sm(global_e2_node_id_t* id, Interval inter, tc_cb* handler);

void rm_report_tc_sm(int);

void control_tc_sm(global_e2_node_id_t* id, tc_ctrl_msg_t* ctrl);

tc_ctrl_msg_t tc_gen_mod_bdp_pcr(uint32_t drb_sz, int64_t tstamp);

tc_ctrl_msg_t tc_gen_add_codel_queue(uint32_t interval_ms, uint32_t target_ms);

tc_ctrl_msg_t tc_gen_add_ecn_queue(uint32_t interval_ms, uint32_t target_ms);

tc_ctrl_msg_t tc_gen_add_fifo_queue(void);

tc_ctrl_msg_t tc_gen_add_osi_cls(int32_t src_port, int32_t dst_port, int32_t protocol, int32_t src_addr, int32_t dst_addr, uint32_t dst_queue);

tc_ctrl_msg_t tc_gen_mod_shaper(uint32_t shaper_id, uint32_t time_window_ms, uint32_t max_rate_kbps, uint32_t active);

//////////////////////////////////////
// GTP SM   
/////////////////////////////////////

struct swig_gtp_ind_msg_t{
  std::vector<gtp_ngu_t_stats_t> gtp_stats; 
  int64_t tstamp;
};

struct gtp_cb {
    virtual void handle(swig_gtp_ind_msg_t* a) = 0;
    virtual ~gtp_cb() {}
};

int report_gtp_sm(global_e2_node_id_t* id, Interval inter, gtp_cb* handler);

void rm_report_gtp_sm(int);

//////////////////////////////////////
// KPM SM
/////////////////////////////////////

struct kpm_cb {
    virtual void handle(kpm_ind_data_t* a) = 0;
    virtual ~kpm_cb() {}
};

struct swig_kpm_ind_msg_t {
  std::vector<std::string> records;
  int64_t tstamp;
};

struct kpm_moni_cb {
  virtual void handle(swig_kpm_ind_msg_t* a) = 0;
  virtual ~kpm_moni_cb() {}
};

int report_kpm_sm(global_e2_node_id_t* id, kpm_sub_data_t* sub, kpm_cb* handler);

void rm_report_kpm_sm(int);

// Build a KPM subscription from the node-advertised KPM RAN function definition.
// Returns -1 when KPM is unsupported for the node or no compatible report style is found.
int report_kpm_sm_auto(global_e2_node_id_t* id, uint64_t period_ms, kpm_cb* handler);

// Same auto-subscription as report_kpm_sm_auto(), but with built-in C-side monitoring logs.
int report_kpm_sm_auto_moni(global_e2_node_id_t* id, uint64_t period_ms);

// Auto-subscription with parsed KPM records delivered to Python callback.
int report_kpm_sm_auto_py(global_e2_node_id_t* id, uint64_t period_ms, kpm_moni_cb* handler);

//////////////////////////////////////
// RC SM
/////////////////////////////////////

struct rc_cb {
    virtual void handle(rc_ind_data_t* a) = 0;
    virtual ~rc_cb() {}
};

int report_rc_sm(global_e2_node_id_t* id, rc_sub_data_t* sub, rc_cb* handler);

void rm_report_rc_sm(int);

void control_rc_sm(global_e2_node_id_t* id, rc_ctrl_req_data_t* ctrl);

#endif
