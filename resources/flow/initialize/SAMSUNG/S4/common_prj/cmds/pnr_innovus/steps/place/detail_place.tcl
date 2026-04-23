# detail_place.tcl
# Detail placement for Innovus PnR

proc detail_place {} {
    puts "INFO: Starting detail placement..."
    refine_place -effort high
    puts "INFO: Detail placement completed."
}
