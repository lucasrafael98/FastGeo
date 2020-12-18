import grid,heatmap
import datetime, csv

keep_running = True
print("Module Online: History.")
f = open("./data/time_history.csv", "w+", newline='')
writer = csv.writer(f, delimiter=',')
writer.writerow(["update","display"])
csvlist = []

while(keep_running):
    next_command = eval(input())
    start = datetime.datetime.now()
    if(next_command[0] == "update"):
        grid.grid_update(next_command[1:])
    elif(next_command[0] == "shm"):
        heatmap.prepare_heatmap_grid(next_command[1:])
    elif(next_command[0] == "chm"):
        heatmap.prepare_heatmap_square_grid(next_command[1:])
    else:
        print("ERROR: invalid command.")
    csvlist.append((datetime.datetime.now() - start).total_seconds())
    if(len(csvlist) == 2):
        writer.writerow(csvlist)
        csvlist = []
        f.flush()
    print('_')
