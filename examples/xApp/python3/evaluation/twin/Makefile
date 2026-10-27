# Builds the actuator out of tree against the pinned ns-O-RAN FlexRIC build (~/flexric-taap, E2AP v1.01,
# KPM v3.00); that tree is only read. Output goes to $(OUT) (default: ./build).
FLEXRIC_TAAP ?= $(HOME)/flexric-taap
OUT ?= build
SRC := $(FLEXRIC_TAAP)/src
BLD := $(FLEXRIC_TAAP)/build
CFLAGS := -g -std=gnu11 -W -Wall -Wno-unused-parameter -Wno-unused-function -DASN -DE2AP_V1 -DKPM_V3_00 \
  -DSERVICE_MODEL_DIR_PATH=\"/\" -DSQLITE3_XAPP -DNR_RRC_VERSION=17.3.0 \
  -DFLEXRIC_INSTALL_PREFIX=\"$(FLEXRIC_TAAP)/install\" \
  -I$(SRC) -I$(BLD)/examples/xApp/c/monitor/RRC_MESSAGES -I$(SRC)/sm/rc_sm/ie/asn
LIBS := $(BLD)/src/xApp/libe42_xapp.a -pthread -lsctp -ldl $(BLD)/examples/xApp/c/monitor/RRC_MESSAGES/libasn1_nr_rrc.a

$(OUT)/xapp_appweaver_actuator: xapp_appweaver_actuator.c
	mkdir -p $(OUT)
	cc $(CFLAGS) $(SRC)/util/alg_ds/alg/defer.c xapp_appweaver_actuator.c -o $@ $(LIBS)

clean:
	rm -rf $(OUT)
