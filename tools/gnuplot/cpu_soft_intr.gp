# expects to be called with gnuplot -e "data='filename'" cpu_soft_intr.gp 
# assumes data is collected via collectl plot command
# assumes data file has column header line un-commented
# assumes 32 cores on a dual socket machine

set terminal pngcairo size 1920,1080 enhanced font 'Verdana,14'
set output sprintf("%s_cpu_soft_intr.png",data)
set autoscale fix
set xdata time
set key autotitle columnhead
set timefmt "%s"
set format x "%Y-%m-%d %H:%M:%S"
set ylabel "Soft%"
set xtics rotate
set grid ytics
set grid xtics


cpu(n) = sprintf("[CPU:%d]Soft%",n)
set multiplot layout 2,2 title "Physical vs HyperThreads" font 'Verdana, 14'
set title 'CPU 0 Physical Core Soft Interrupts'
plot for [i = 0:7] data using 'UTC':cpu(i) title columnheader with lines
set title 'CPU 0 Logical Core Soft Interrupts'
plot for [i = 8:15] data using 'UTC':cpu(i) title columnheader with lines
set title 'CPU 1 Physical Core Soft Interrupts'
plot for [i = 16:23] data using 'UTC':cpu(i) title columnheader with lines
set title 'CPU 1 Logical Core Soft Interrupts'
plot for [i = 24:31] data using 'UTC':cpu(i) title columnheader with lines
