/*
 * TC service model with a real data plane (AppWeaver demo D3).
 *
 * Same E2SM-TC interface as sm_tc.c, but a queue control (add/mod FIFO, CoDel, ECN-CoDel) is applied
 * to a real Linux queue: the agent runs the hook named by the environment variable TC_DP_HOOK as
 *   $TC_DP_HOOK fifo
 *   $TC_DP_HOOK codel <target_ms> <interval_ms>
 *   $TC_DP_HOOK ecn_codel <target_ms> <interval_ms>
 * (evaluation/demos/tc_dataplane/tc_hook.sh replaces the child qdisc of the bottleneck). Other control
 * types (classifier, policer, scheduler, shaper, pacer) are acknowledged and logged, not applied.
 * Indication statistics stay the emulator's (fill_rnd_data_tc): the demo measures RTT and throughput on
 * the link itself, not through the TC indication.
 */
#include "sm_tc.h"
#include "../../../test/rnd/fill_rnd_data_tc.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>

void init_tc_sm(void)
{
  // No allocation needed
}

void free_tc_sm(void)
{
  // No allocation needed
}

bool read_tc_sm(void* data)
{
  assert(data != NULL);
  tc_ind_data_t* tc = (tc_ind_data_t*)data;
  fill_tc_ind_data(tc);
  return true;
}

void read_tc_setup_sm(void* data)
{
  assert(data != NULL);
  assert(0 !=0 && "Not supported");
}

static int run_hook(char const* args)
{
  char const* hook = getenv("TC_DP_HOOK");
  if (hook == NULL) {
    fprintf(stderr, "[TC-DP] TC_DP_HOOK not set: control '%s' not applied\n", args);
    return -1;
  }
  char cmd[512];
  snprintf(cmd, sizeof(cmd), "%s %s", hook, args);
  int const rc = system(cmd);
  fprintf(stderr, "[TC-DP] %s -> rc=%d\n", cmd, rc);
  fflush(stderr);
  return rc;
}

static void apply_queue(tc_queue_e type, uint32_t target_ms, uint32_t interval_ms)
{
  char args[128];
  if (type == TC_QUEUE_FIFO)
    snprintf(args, sizeof(args), "fifo");
  else if (type == TC_QUEUE_CODEL)
    snprintf(args, sizeof(args), "codel %u %u", target_ms, interval_ms);
  else if (type == TC_QUEUE_ECN_CODEL)
    snprintf(args, sizeof(args), "ecn_codel %u %u", target_ms, interval_ms);
  else
    return;
  run_hook(args);
}

sm_ag_if_ans_t write_ctrl_tc_sm(void const* data)
{
  assert(data != NULL);
  tc_ctrl_req_data_t const* ctrl = (tc_ctrl_req_data_t const*)data;
  tc_ctrl_msg_e const t = ctrl->msg.type;

  assert(t == TC_CTRL_SM_V0_CLS || t == TC_CTRL_SM_V0_PLC
      || t == TC_CTRL_SM_V0_QUEUE || t ==TC_CTRL_SM_V0_SCH
      || t == TC_CTRL_SM_V0_SHP || t == TC_CTRL_SM_V0_PCR);

  if (t == TC_CTRL_SM_V0_QUEUE) {
    tc_ctrl_queue_t const* q = &ctrl->msg.q;
    if (q->act == TC_CTRL_ACTION_SM_V0_ADD) {
      uint32_t const tgt = q->add.type == TC_QUEUE_CODEL ? q->add.codel.target_ms : q->add.ecn.target_ms;
      uint32_t const itv = q->add.type == TC_QUEUE_CODEL ? q->add.codel.interval_ms : q->add.ecn.interval_ms;
      apply_queue(q->add.type, tgt, itv);
    } else if (q->act == TC_CTRL_ACTION_SM_V0_MOD) {
      uint32_t const tgt = q->mod.type == TC_QUEUE_CODEL ? q->mod.codel.target_ms : q->mod.ecn.target_ms;
      uint32_t const itv = q->mod.type == TC_QUEUE_CODEL ? q->mod.codel.interval_ms : q->mod.ecn.interval_ms;
      apply_queue(q->mod.type, tgt, itv);
    } else if (q->act == TC_CTRL_ACTION_SM_V0_DEL) {
      run_hook("fifo");
    }
  } else {
    fprintf(stderr, "[TC-DP] control type %d acknowledged, not applied to the data plane\n", (int)t);
  }

  sm_ag_if_ans_t ans = {.type = CTRL_OUTCOME_SM_AG_IF_ANS_V0};
  ans.ctrl_out.type = TC_AGENT_IF_CTRL_ANS_V0;
  return ans;
}
