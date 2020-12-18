import edge_bundling, adjacencies, heatmap, generic_transitions
import datetime, csv

keep_running = True
print("Module Online: Recent.")
f = open("./data/time_recent.csv", "w+", newline='')
writer = csv.writer(f, delimiter=',')
writer.writerow(["remove","update","display"])
csvlist = []

while(keep_running):
    next_command = eval(input())
    start = datetime.datetime.now()
    if(next_command[0] == "bundle"):
        edge_bundling.main(next_command[1:])
    elif(next_command[0] == "update"):
        generic_transitions.update_new(next_command[1:])
    elif(next_command[0] == "remove"):
        generic_transitions.remove_old(next_command[1:])
    elif(next_command[0] == "adj"):
        adjacencies.display_adjacencies(next_command[1:])
    elif(next_command[0] == "hm"):
        heatmap.prepare_heatmap(next_command[1:])
    else:
        print("ERROR: invalid command.")
    csvlist.append((datetime.datetime.now() - start).total_seconds())
    if(len(csvlist) == 3):
        writer.writerow(csvlist)
        csvlist = []
        f.flush()
    print('_')
