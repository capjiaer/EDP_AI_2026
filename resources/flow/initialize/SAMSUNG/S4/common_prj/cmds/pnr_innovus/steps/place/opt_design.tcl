# opt_design.tcl
# Post-placement optimization

proc opt_design {} {
    puts "INFO: Starting post-place optimization..."
    opt_design -effort high
    puts "INFO: Post-place optimization completed."
}
