import ongoing
import datetime, csv

keep_running = True
print("Module Online: Ongoing.")
f = open("./data/time_ongoing.csv", "w+", newline='')
writer = csv.writer(f, delimiter=',')
writer.writerow(["remove","update"])
csvlist = []

while(keep_running):
    next_command = eval(input())
    start = datetime.datetime.now()
    if(next_command[0] == "consec"):
        ongoing.consecutive_lines(next_command[1])
    elif(next_command[0] == "stops"):
        ongoing.check_stop_events(next_command[1:])
    else:
        print("ERROR: invalid command.")
    csvlist.append((datetime.datetime.now() - start).total_seconds())
    if(len(csvlist) == 2):
        writer.writerow(csvlist)
        csvlist = []
        f.flush()
    print('_')
