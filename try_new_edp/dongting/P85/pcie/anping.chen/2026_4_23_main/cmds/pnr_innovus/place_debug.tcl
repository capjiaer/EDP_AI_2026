# ============================================================
# EDP Debug Mode
# Step: place  Tool: pnr_innovus
# Source this file in your tool's Tcl shell for interactive debug.
# ============================================================

# ============================================================
# Phase 1: Source
# ============================================================

# --- pnr_innovus/steps/place ---
source C:/Users/anping.chen/Desktop/rewrite_edp_continue/new_edp/resources/flow/initialize/SAMSUNG/S4/common_prj/cmds/pnr_innovus/steps/place/global_place.tcl
source C:/Users/anping.chen/Desktop/rewrite_edp_continue/new_edp/resources/flow/initialize/SAMSUNG/S4/common_prj/cmds/pnr_innovus/steps/place/detail_place.tcl
source C:/Users/anping.chen/Desktop/rewrite_edp_continue/new_edp/resources/flow/initialize/SAMSUNG/S4/common_prj/cmds/pnr_innovus/steps/place/opt_design.tcl

# --- hooks/pnr_innovus/place (proc definitions) ---
source C:/Users/anping.chen/Desktop/rewrite_edp_continue/try_new_edp/dongting/P85/pcie/anping.chen/2026_4_23_main/hooks/pnr_innovus/place/detail_place.post
source C:/Users/anping.chen/Desktop/rewrite_edp_continue/try_new_edp/dongting/P85/pcie/anping.chen/2026_4_23_main/hooks/pnr_innovus/place/detail_place.pre
source C:/Users/anping.chen/Desktop/rewrite_edp_continue/try_new_edp/dongting/P85/pcie/anping.chen/2026_4_23_main/hooks/pnr_innovus/place/detail_place.replace
source C:/Users/anping.chen/Desktop/rewrite_edp_continue/try_new_edp/dongting/P85/pcie/anping.chen/2026_4_23_main/hooks/pnr_innovus/place/global_place.post
source C:/Users/anping.chen/Desktop/rewrite_edp_continue/try_new_edp/dongting/P85/pcie/anping.chen/2026_4_23_main/hooks/pnr_innovus/place/global_place.pre
source C:/Users/anping.chen/Desktop/rewrite_edp_continue/try_new_edp/dongting/P85/pcie/anping.chen/2026_4_23_main/hooks/pnr_innovus/place/global_place.replace
source C:/Users/anping.chen/Desktop/rewrite_edp_continue/try_new_edp/dongting/P85/pcie/anping.chen/2026_4_23_main/hooks/pnr_innovus/place/opt_design.post
source C:/Users/anping.chen/Desktop/rewrite_edp_continue/try_new_edp/dongting/P85/pcie/anping.chen/2026_4_23_main/hooks/pnr_innovus/place/opt_design.pre
source C:/Users/anping.chen/Desktop/rewrite_edp_continue/try_new_edp/dongting/P85/pcie/anping.chen/2026_4_23_main/hooks/pnr_innovus/place/opt_design.replace
source C:/Users/anping.chen/Desktop/rewrite_edp_continue/try_new_edp/dongting/P85/pcie/anping.chen/2026_4_23_main/hooks/pnr_innovus/place/step.post
source C:/Users/anping.chen/Desktop/rewrite_edp_continue/try_new_edp/dongting/P85/pcie/anping.chen/2026_4_23_main/hooks/pnr_innovus/place/step.pre

# ============================================================
# Config Variables
# Generated from: base -> overlay -> user_config
# See place_config.tcl for details and variable tracing
# ============================================================

source C:/Users/anping.chen/Desktop/rewrite_edp_continue/try_new_edp/dongting/P85/pcie/anping.chen/2026_4_23_main/cmds/pnr_innovus/place_config.tcl

# Load debug CLI
source C:/Users/anping.chen/Desktop/rewrite_edp_continue/new_edp/resources/common_packages/tcl_packages/default/edp_debug.tcl