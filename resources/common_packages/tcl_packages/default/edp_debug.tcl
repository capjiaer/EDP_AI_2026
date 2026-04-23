# ============================================================
# edp_debug.tcl — EDP Debug Mode Interactive CLI
#
# Reads plan from edp() namespace (set by config.tcl):
#   edp(step)           - step name
#   edp(tool)           - tool name
#   edp(sub_steps)      - ordered list of sub_steps
#   edp(invoked_hooks)  - active hooks
#
# Hook proc naming convention:
#   {step}_step_pre / {step}_step_post          step-level
#   {step}_{sub}_pre / {step}_{sub}_post        sub_step-level
#
# Usage: source your_debug.tcl, then type edp_help for commands.
# ============================================================

namespace eval edp_debug {
    variable plan {}
    variable done
    variable current_idx 0
}

proc edp_debug_init {} {
    global edp

    # Build plan from edp(sub_steps)
    set step $edp(step)
    set plan {}
    foreach sub $edp(sub_steps) {
        set pre "${step}_${sub}_pre"
        set post "${step}_${sub}_post"
        lappend plan [list $sub $pre $post]
    }
    set edp_debug::plan $plan
    set edp_debug::current_idx 0
    array set edp_debug::done {}

    set total [llength $plan]
    puts ""
    puts "=========================================="
    puts " EDP Debug Mode — $step"
    puts " Sub-steps ($total): [edp_debug::_plan_string]"
    if {[info exists edp(invoked_hooks)] && $edp(invoked_hooks) ne ""} {
        puts " Active hooks: $edp(invoked_hooks)"
    }
    puts " Type 'edp_help' for commands"
    puts "=========================================="
    puts ""
}

# --- Internal helpers ---

proc edp_debug::_plan_string {} {
    set names {}
    foreach item $edp_debug::plan {
        lappend names [lindex $item 0]
    }
    return [join $names " -> "]
}

proc edp_debug::_sub_exists {sub} {
    foreach item $edp_debug::plan {
        if {[lindex $item 0] eq $sub} { return 1 }
    }
    return 0
}

proc edp_debug::_find_idx {sub} {
    set idx 0
    foreach item $edp_debug::plan {
        if {[lindex $item 0] eq $sub} { return $idx }
        incr idx
    }
    return -1
}

proc edp_debug::_run_one {sub pre_hook post_hook} {
    puts "--- Running: $sub ---"
    if {$pre_hook ne "" && [info procs $pre_hook] ne ""} {
        puts "  \[hook\] $pre_hook"
        if {[catch {$pre_hook} err]} { puts "  \[hook error\] $err" }
    }
    if {[catch {$sub} err]} {
        puts "  \[error\] $err"
    }
    if {$post_hook ne "" && [info procs $post_hook] ne ""} {
        puts "  \[hook\] $post_hook"
        if {[catch {$post_hook} err]} { puts "  \[hook error\] $err" }
    }
    set edp_debug::done($sub) 1
    puts "--- Done: $sub ---"
}

# --- Public Commands ---

proc edp_help {} {
    puts ""
    puts "EDP Debug Commands:"
    puts ""
    puts "  edp_steplist          Show plan + active hooks + status"
    puts "  edp_vars ?pattern?    Show variables (optional filter)"
    puts ""
    puts "  edp_next              Run next sub_step"
    puts "  edp_run <sub>         Run specific sub_step"
    puts "  edp_run_rest          Run all remaining sub_steps"
    puts "  edp_run_to <sub>      Run up to (and including) a sub_step"
    puts "  edp_skip <sub>        Skip a sub_step (mark as done)"
    puts ""
    puts "  edp_reset ?sub?       Reset from sub_step onwards (default: all)"
    puts ""
}

proc edp_steplist {} {
    global edp
    set step $edp(step)
    set step_pre "${step}_step_pre"
    set step_post "${step}_step_post"

    puts ""
    puts "Step: $step  Tool: $edp(tool)"

    if {[info procs $step_pre] ne ""} {
        puts "  \[pre\]  $step_pre"
    }

    set idx 0
    foreach item $edp_debug::plan {
        set sub [lindex $item 0]
        set pre [lindex $item 1]
        set post [lindex $item 2]

        if {[info exists edp_debug::done($sub)]} {
            set mark "DONE"
        } elseif {$idx == $edp_debug::current_idx} {
            set mark "NEXT"
        } else {
            set mark "    "
        }

        puts "  $mark  $sub"

        if {[info procs $pre] ne ""} {
            puts "         \[pre\]    $pre"
        }
        if {[info procs $post] ne ""} {
            puts "         \[post\]   $post"
        }

        incr idx
    }

    if {[info procs $step_post] ne ""} {
        puts "  \[post\] $step_post"
    }
    puts ""
}

proc edp_vars {{pattern "*"}} {
    set count 0
    foreach var [info vars] {
        if {[string match "edp_debug*" $var]} { continue }
        if {[string match "tcl_*" $var]} { continue }

        if {[array exists $var]} {
            foreach elem [lsort [array names $var]] {
                set full "${var}($elem)"
                if {[string match $pattern $full] || [string match $pattern $var]} {
                    puts "  set $full {[set ${var}($elem)]}"
                    incr count
                }
            }
        } else {
            if {[string match $pattern $var]} {
                puts "  set $var {[set $var]}"
                incr count
            }
        }
    }
    puts ""
    puts "  ($count variables shown)"
}

proc edp_next {} {
    global edp

    if {$edp_debug::current_idx >= [llength $edp_debug::plan]} {
        puts "No more sub_steps to run."
        return
    }

    # step pre hook on first run
    if {$edp_debug::current_idx == 0} {
        set step_pre "${edp(step)}_step_pre"
        if {[info procs $step_pre] ne ""} {
            puts "  \[step pre\] $step_pre"
            if {[catch {$step_pre} err]} { puts "  \[step pre error\] $err" }
        }
    }

    # skip already-done sub_steps
    while {$edp_debug::current_idx < [llength $edp_debug::plan]} {
        set item [lindex $edp_debug::plan $edp_debug::current_idx]
        set sub [lindex $item 0]
        if {![info exists edp_debug::done($sub)]} { break }
        puts "  \[skip\] $sub (already done)"
        incr edp_debug::current_idx
    }

    if {$edp_debug::current_idx >= [llength $edp_debug::plan]} {
        puts "All remaining sub_steps were skipped."
        return
    }

    set item [lindex $edp_debug::plan $edp_debug::current_idx]
    set sub [lindex $item 0]
    set pre [lindex $item 1]
    set post [lindex $item 2]

    edp_debug::_run_one $sub $pre $post
    incr edp_debug::current_idx

    if {$edp_debug::current_idx >= [llength $edp_debug::plan]} {
        puts ""
        puts "All sub_steps completed."
        set step_post "${edp(step)}_step_post"
        if {[info procs $step_post] ne ""} {
            puts "  \[step post\] $step_post"
            if {[catch {$step_post} err]} { puts "  \[step post error\] $err" }
        }
    }
}

proc edp_run {sub} {
    if {![edp_debug::_sub_exists $sub]} {
        puts "Unknown sub_step: $sub"
        puts "Available: [edp_debug::_plan_string]"
        return
    }

    set idx [edp_debug::_find_idx $sub]
    set item [lindex $edp_debug::plan $idx]
    set pre [lindex $item 1]
    set post [lindex $item 2]

    edp_debug::_run_one $sub $pre $post
}

proc edp_run_rest {} {
    if {$edp_debug::current_idx >= [llength $edp_debug::plan]} {
        puts "No more sub_steps to run."
        return
    }

    while {$edp_debug::current_idx < [llength $edp_debug::plan]} {
        edp_next
    }
}

proc edp_run_to {sub} {
    if {![edp_debug::_sub_exists $sub]} {
        puts "Unknown sub_step: $sub"
        puts "Available: [edp_debug::_plan_string]"
        return
    }

    set target [edp_debug::_find_idx $sub]

    while {$edp_debug::current_idx <= $target} {
        edp_next
    }

    puts ""
    puts "Stopped after: $sub"
}

proc edp_skip {sub} {
    if {![edp_debug::_sub_exists $sub]} {
        puts "Unknown sub_step: $sub"
        return
    }

    set edp_debug::done($sub) 1
    set idx [edp_debug::_find_idx $sub]
    if {$idx == $edp_debug::current_idx} {
        incr edp_debug::current_idx
    }
    puts "Skipped: $sub"
}

proc edp_reset {{sub ""}} {
    if {$sub eq ""} {
        array set edp_debug::done {}
        set edp_debug::current_idx 0
        puts "Reset: all sub_steps cleared."
    } else {
        if {![edp_debug::_sub_exists $sub]} {
            puts "Unknown sub_step: $sub"
            return
        }

        set idx [edp_debug::_find_idx $sub]
        set cleared {}
        for {set i $idx} {$i < [llength $edp_debug::plan]} {incr i} {
            set s [lindex [lindex $edp_debug::plan $i] 0]
            catch {unset edp_debug::done($s)}
            lappend cleared $s
        }
        set edp_debug::current_idx $idx
        puts "Reset from: $sub ([join $cleared ", "])"
    }
}

# --- Auto-init (config.tcl with edp() vars must be sourced before this file) ---
edp_debug_init
