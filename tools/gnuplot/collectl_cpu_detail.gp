# call with gnuplot -e "data='reads/data-1-20161114-180944.cpu';title='Baseline EC 4+2 - 4MiB Reads'" collectl_cpu_detail.gp
# assumes data is collected via collectl plot command
# assumes data file has column header line un-commented
# assumes 32 cores on a dual socket machine

set terminal pngcairo size 1920,1080 enhanced font 'Verdana,14'
set output sprintf("%s_user.png",data)
set title sprintf("%s",title)
set autoscale fix
set xdata time
set key outside right center
set timefmt "%s"
set format x "%Y-%m-%d %H:%M:%S"
set ylabel "Percentage"
set yrange [0:100]
set xtics rotate
set grid ytics
set grid xtics


cpu_user(n) = sprintf("[CPU:%d]User%",n)
cpu_sys(n) = sprintf("[CPU:%d]Sys%",n)
cpu_tot(n) = sprintf("[CPU:%d]Totl%",n)
cpu_idl(n) = sprintf("[CPU:%d]Idle%",n)
plot for [i = 0:31] data using 'UTC':cpu_user(i) title columnheader  with lines smooth bezier lc rgb "green",\
for [i = 0:31] data using 'UTC':cpu_sys(i) title columnheader with lines smooth bezier lc rgb "blue",\
for [i = 0:31] data using 'UTC':cpu_idl(i) title columnheader with lines smooth bezier lc rgb "red"
