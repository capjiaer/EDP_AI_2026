# global_place.tcl
# Global placement for Innovus PnR

proc global_place {} {
    puts "INFO: Starting global placement..."
    set_placement -effort high
    puts "INFO: Global placement completed."
}
