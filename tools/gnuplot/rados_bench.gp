# expects to be called with gnuplot rados_bench.gp
# expects client data files to be cleaned via:
# sed -i '/sec Cur/d' client-#.dat
# sed -i '/min lat/d' client-#.dat
# expects data files to be named client-#.dat

set terminal pngcairo size 1920,1200 enhanced font 'Verdana,12'
set output 'rados_client_activity.png'
set title 'Client Throughput 4MiB Objects 12hr Write Test'
set autoscale noextend
set xdata time
set timefmt "%Y-%m-%d %H:%M:%S"
set format x "%Y-%m-%d %H:%M:%S"
set ylabel "Avg MiB/s"
set xtics rotate
set grid ytics
set grid xtics

# I set the clusterstats as labels, this is sadly by hand
#set label 1 "1.63%, 687,908" at "2016-12-27 14:00:00",1200 rotate
#set label 2 "11.24% 4,806,071" at "2016-12-27 15:00:00",1200 rotate
#set label 3 "20.69% 8,813,916" at "2016-12-27 16:00:00",1200 rotate
#set label 4 "29.42% 12,396,204" at "2016-12-27 17:00:00",1200 rotate
#set label 5 "39.00% 16,426,570" at "2016-12-27 18:00:00",1200 rotate
#set label 6 "48.32% 20,353,920" at "2016-12-27 19:00:00",1200 rotate
#set label 7 "57.91% 24,396,559" at "2016-12-27 20:00:00",1200 rotate
#set label 8 "67.17% 28,295,581" at "2016-12-27 21:00:00",1200 rotate
#set label 9 "71.45% 30,107,915" at "2016-12-27 22:00:00",1200 rotate
#set label 10 "71.45% 30,107,915" at "2016-12-27 23:00:00",1200 rotate

file(n) = sprintf("client-%d.dat",n)
plot for [i = 1:4] file(i) using 1:7 title sprintf('Client-%d',i) with lines
