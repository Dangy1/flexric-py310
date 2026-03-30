/* File : example.i */
%module(directors="4") xapp_sdk
%include "std_string.i"
%include "std_vector.i"
%include "carrays.i"
%include <typemaps.i>

%{
  #include "swig_wrapper.h"

#ifdef E2AP_V1
  #include "../../lib/e2ap/v1_01/e2ap_types/common/e2ap_global_node_id.h"
  #include "../../lib/e2ap/v1_01/e2ap_types/common/e2ap_plmn.h"
  #include "../../lib/e2ap/v1_01/e2ap_types/common/e2ap_ran_function.h"
#elif E2AP_V2
  #include "../../lib/e2ap/v2_03/e2ap_types/common/e2ap_global_node_id.h"
  #include "../../lib/e2ap/v2_03/e2ap_types/common/e2ap_plmn.h"
  #include "../../lib/e2ap/v2_03/e2ap_types/common/e2ap_ran_function.h"
#elif E2AP_V3
  #include "../../lib/e2ap/v3_01/e2ap_types/common/e2ap_global_node_id.h"
  #include "../../lib/e2ap/v3_01/e2ap_types/common/e2ap_plmn.h"
  #include "../../lib/e2ap/v3_01/e2ap_types/common/e2ap_ran_function.h"
#endif

 #include "../../util/byte_array.h"
  #include "../../sm/mac_sm/ie/mac_data_ie.h"
  #include "../../sm/rlc_sm/ie/rlc_data_ie.h"
  #include "../../sm/pdcp_sm/ie/pdcp_data_ie.h"
  #include "../../sm/slice_sm/ie/slice_data_ie.h"
  #include "../../sm/tc_sm/ie/tc_data_ie.h"
  #include "../../sm/gtp_sm/ie/gtp_data_ie.h"
  #include "../../sm/rc_sm/ie/rc_data_ie.h"
#ifdef KPM_V2_01
  #include "../../sm/kpm_sm/kpm_sm_v02.01/ie/kpm_data_ie.h"
#elif defined(KPM_V2_03)
  #include "../../sm/kpm_sm/kpm_sm_v02.03/ie/kpm_data_ie.h"
#elif defined(KPM_V3_00)
  #include "../../sm/kpm_sm/kpm_sm_v03.00/ie/kpm_data_ie.h"
#endif
%}

#ifdef SWIGPYTHON
%pythonbegin %{
import ctypes as _ctypes
import ctypes.util as _ctypes_util
import os as _flexric_os
import sys as _flexric_sys

_FLEXRIC_BUILD_PYTHON = (FLEXRIC_PYTHON_VERSION_MAJOR, FLEXRIC_PYTHON_VERSION_MINOR)


def _flexric_require_matching_python():
    current = _flexric_sys.version_info[:2]
    if current != _FLEXRIC_BUILD_PYTHON:
        expected = "%d.%d" % _FLEXRIC_BUILD_PYTHON
        running = "%d.%d" % current
        raise ImportError(
            "xapp_sdk was built for Python %s but is being imported by Python %s. "
            "Reconfigure FlexRIC with `cmake -B build -DPython3_EXECUTABLE=$(which python3) ..` "
            "and rebuild, or run the xApp with the matching interpreter." % (expected, running)
        )


def _flexric_require_libsctp():
    candidates = ["libsctp.so.1"]
    detected = _ctypes_util.find_library("sctp")
    if detected and detected not in candidates:
        candidates.append(detected)

    last_error = None
    for candidate in candidates:
        try:
            _ctypes.CDLL(candidate, mode=getattr(_ctypes, "RTLD_GLOBAL", 0))
            return
        except OSError as exc:
            last_error = exc

    raise ImportError(
        "xapp_sdk requires libsctp.so.1 (the SCTP runtime library). "
        "Install `libsctp1` on Debian/Ubuntu or `lksctp-tools` on RHEL/Rocky, then retry."
    ) from last_error


def _flexric_preload_shared():
    here = _flexric_os.path.abspath(_flexric_os.path.dirname(__file__))
    candidates = [
        _flexric_os.path.join(here, "..", "..", "..", "src", "xApp", "libe42_xapp_shared.so"),
        _flexric_os.path.join(here, "libe42_xapp_shared.so"),
        "/usr/local/lib/libe42_xapp_shared.so",
    ]

    for candidate in candidates:
        candidate = _flexric_os.path.abspath(candidate)
        if not _flexric_os.path.exists(candidate):
            continue
        try:
            _ctypes.CDLL(candidate, mode=getattr(_ctypes, "RTLD_GLOBAL", 0))
            return
        except OSError as exc:
            raise ImportError(
                "Failed to load required FlexRIC library %s: %s. "
                "Build FlexRIC with the selected Python interpreter and make sure the shared library is reachable."
                % (candidate, exc)
            ) from exc


_flexric_require_matching_python()
_flexric_require_libsctp()
_flexric_preload_shared()
%}

/* uintXX_t mapping: Python -> C */
%typemap(in) uint8_t {
    $1 = (uint8_t) PyInt_AsLong($input);
}
%typemap(in) uint16_t {
    $1 = (uint16_t) PyInt_AsLong($input);
}
%typemap(in) uint32_t {
    $1 = (uint32_t) PyInt_AsLong($input);
}
%typemap(in) uint64_t {
    $1 = (uint64_t) PyInt_AsLong($input);
}

/* intXX_t mapping: Python -> C */
%typemap(in) int8_t {
    $1 = (int8_t) PyInt_AsLong($input);
}
%typemap(in) int16_t {
    $1 = (int16_t) PyInt_AsLong($input);
}
%typemap(in) int32_t {
    $1 = (int32_t) PyInt_AsLong($input);
}
%typemap(in) int64_t {
    $1 = (int64_t) PyInt_AsLong($input);
}

/* uintXX_t mapping: C -> Python */
%typemap(out) uint8_t {
    $result = PyInt_FromLong((long) $1);
}
%typemap(out) uint16_t {
    $result = PyInt_FromLong((long) $1);
}
%typemap(out) uint32_t {
    $result = PyInt_FromLong((long) $1);
}
%typemap(out) uint64_t {
    $result = PyInt_FromLong((long) $1);
}

/* intXX_t mapping: C -> Python */
%typemap(out) int8_t {
    $result = PyInt_FromLong((long) $1);
}
%typemap(out) int16_t {
    $result = PyInt_FromLong((long) $1);
}
%typemap(out) int32_t {
    $result = PyInt_FromLong((long) $1);
}
%typemap(out) int64_t {
    $result = PyInt_FromLong((long) $1);
}

#endif

%feature("director") mac_cb;
%feature("director") rlc_cb;
%feature("director") pdcp_cb;
%feature("director") slice_cb;
%feature("director") gtp_cb;
%feature("director") tc_cb;
%feature("director") kpm_cb;
%feature("director") kpm_moni_cb;
%feature("director") rc_cb;

/* Avoid wrapping helper APIs known to cause unresolved C++-mangled symbols. */
%ignore eq_tc_cls;
%ignore cp_e2sm_rc_act_def_frmt_3;

namespace std {
  %template(IntVector) vector<int>;
  %template(E2NodeVector) vector<E2Node>;
  %template(RANVector) vector<ran_function_t>;
  %template(MACStatsVector) vector<mac_ue_stats_impl_t>;
  %template(RLC_RBStatsVector) vector<rlc_radio_bearer_stats_t>;
  %template(PDCP_RBStatsVector) vector<pdcp_radio_bearer_stats_t>;
  %template(StringVector) vector<std::string>;
  %template(SLICE_slicesStatsVector) vector<swig_fr_slice_t>;
  %template(SLICE_UEsStatsVector) vector<ue_slice_assoc_t>;
  %template(GTP_NGUTStatsVector) vector<gtp_ngu_t_stats_t>;
}


%array_class(ue_slice_assoc_t, ue_slice_assoc_array);
%array_class(fr_slice_t, slice_array);
%array_class(uint32_t, del_dl_array);
%array_class(uint32_t, del_ul_array);

%include "swig_wrapper.h"
%include "../../util/byte_array.h"

%include "../../lib/e2ap/e2ap_global_node_id_wrapper.h"
%include "../../lib/e2ap/e2ap_plmn_wrapper.h"
%include "../../lib/e2ap/e2ap_ran_function_wrapper.h"


#ifdef E2AP_V1
  %include "../../lib/e2ap/v1_01/e2ap_types/common/e2ap_global_node_id.h"
  %include "../../lib/e2ap/v1_01/e2ap_types/common/e2ap_plmn.h"
  %include "../../lib/e2ap/v1_01/e2ap_types/common/e2ap_ran_function.h"
#elif defined E2AP_V2
  %include "../../lib/e2ap/v2_03/e2ap_types/common/e2ap_global_node_id.h"
  %include "../../lib/e2ap/v2_03/e2ap_types/common/e2ap_plmn.h"
  %include "../../lib/e2ap/v2_03/e2ap_types/common/e2ap_ran_function.h"
#elif defined E2AP_V3
  %include "../../lib/e2ap/v3_01/e2ap_types/common/e2ap_global_node_id.h"
  %include "../../lib/e2ap/v3_01/e2ap_types/common/e2ap_plmn.h"
  %include "../../lib/e2ap/v3_01/e2ap_types/common/e2ap_ran_function.h"
#endif

%include "../../sm/mac_sm/ie/mac_data_ie.h"
%include "../../sm/rlc_sm/ie/rlc_data_ie.h"
%include "../../sm/pdcp_sm/ie/pdcp_data_ie.h"
%include "../../sm/slice_sm/ie/slice_data_ie.h"
%include "../../sm/tc_sm/ie/tc_data_ie.h"
%include "../../sm/gtp_sm/ie/gtp_data_ie.h"
%include "../../sm/rc_sm/ie/rc_data_ie.h"
#ifdef KPM_V2_01
  %include "../../sm/kpm_sm/kpm_sm_v02.01/ie/kpm_data_ie.h"
#elif defined(KPM_V2_03)
  %include "../../sm/kpm_sm/kpm_sm_v02.03/ie/kpm_data_ie.h"
#elif defined(KPM_V3_00)
  %include "../../sm/kpm_sm/kpm_sm_v03.00/ie/kpm_data_ie.h"
#endif
