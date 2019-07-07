import Tkinter as tk
import tkFileDialog as filedialog
import tkMessageBox as confirmDialog
from ttkHyperlinkLabel import HyperlinkLabel
import sys
import csv
import os
from monitor import monitor
import urllib
import json

if sys.platform.startswith('linux'):
    import subprocess


this = sys.modules[__name__]
this.plugin_version = "1.1.0"
this.update_available = False
this.next_stop = "No route planned"
this.route = []
this.next_wp_label = "Next waypoint: "
this.jumpcountlbl_txt = "Estimated jumps left: "
this.parent = None
this.save_route_path = ""
this.offset_file_path = ""
this.offset = 0
this.jumps_left = 0


def plugin_start(plugin_dir):
    # Check for newer versions
    url = "https://raw.githubusercontent.com/CMDR-Kiel42/EDMC_SpanshRouter/master/version.json"
    response = urllib.urlopen(url)
    latest_version = response.read()

    if response.code == 200 and this.plugin_version != latest_version:
        this.update_available = True

    this.save_route_path = os.path.join(plugin_dir, 'route.csv')
    this.offset_file_path = os.path.join(plugin_dir, 'offset')

    try:
        # Open the last saved route
        with open(this.save_route_path, 'r') as csvfile:
            route_reader = csv.reader(csvfile)

            for row in route_reader:
                this.route.append(row)

            try:
                with open(this.offset_file_path, 'r') as offset_fh:
                    this.offset = int(offset_fh.readline())

            except:
                this.offset = 0

        for row in this.route[this.offset:]:
            this.jumps_left += int(row[1])

        this.next_stop = this.route[this.offset][0]
        copy_waypoint()
    except:
        print("No previously saved route.")


def plugin_stop():
    if this.route.__len__() != 0:
        # Save route for next time
        with open(this.save_route_path, 'w') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(this.route)

        with open(this.offset_file_path, 'w') as offset_fh:
            offset_fh.write(str(this.offset))
    else:
        try:
            os.remove(this.save_route_path)
            os.remove(this.offset_file_path)
        except:
            print("No route to delete")


def update_gui():
    if not this.route.__len__() > 0:
        this.waypoint_prev_btn.grid_remove()
        this.waypoint_btn.grid_remove()
        this.waypoint_next_btn.grid_remove()
        this.jumpcounttxt_lbl.grid_remove()
        this.clear_route_btn.grid_remove()
    else:
        this.waypoint_btn["text"] = this.next_wp_label + this.next_stop
        this.jumpcounttxt_lbl["text"] = this.jumpcountlbl_txt + str(this.jumps_left)
        this.jumpcounttxt_lbl.grid()

        this.waypoint_prev_btn.grid()
        this.waypoint_btn.grid()
        this.waypoint_next_btn.grid()

        if this.offset == 0:
            this.waypoint_prev_btn.config(state=tk.DISABLED)
        else:
            this.waypoint_prev_btn.config(state=tk.NORMAL)

            if this.offset == this.route.__len__()-1:
                this.waypoint_next_btn.config(state=tk.DISABLED)
            else:
                this.waypoint_next_btn.config(state=tk.NORMAL)

        this.clear_route_btn.grid()
        


def copy_waypoint(self=None):
    if sys.platform == "win32":
        this.parent.clipboard_clear()
        this.parent.clipboard_append(this.next_stop)
        this.parent.update()
    else:
        command = subprocess.Popen(["echo", "-n", this.next_stop], stdout=subprocess.PIPE)
        subprocess.Popen(["xclip", "-selection", "c"], stdin=command.stdout)

def goto_next_waypoint(self=None):
    if this.offset < this.route.__len__()-1:
        update_route(1)

def goto_prev_waypoint(self=None):
    if this.offset > 0:
        update_route(-1)

def new_route(self=None):
    filename = filedialog.askopenfilename(filetypes = (("csv files", "*.csv"),))    # show an "Open" dialog box and return the path to the selected file

    if filename.__len__() > 0:
        with open(filename, 'r') as csvfile:
            route_reader = csv.reader(csvfile)

            # Skip the header
            route_reader.next()

            this.jumps_left = 0
            for row in route_reader:
                this.route.append([row[0], row[4]])
                this.jumps_left += int(row[4])

        this.offset = 0
        this.next_stop = this.route[0][0]
        copy_waypoint()
        update_gui()

def clear_route(self=None):
    clear = confirmDialog.askyesno("SpanshRouter","Are you sure you want to clear the current route?")

    if clear:
        this.offset = 0
        this.route = []
        this.next_waypoint = ""
        try:
            os.remove(this.save_route_path)
        except:
            print("No route to delete")
        try:
            os.remove(this.offset_file_path)
        except:
            print("No offset file to delete")

        update_gui()


def update_route(direction=1):
    if direction > 0:
        this.jumps_left -= int(this.route[this.offset][1])
        this.offset += 1
    else:
        this.offset -= 1
        this.jumps_left += int(this.route[this.offset][1])

    if this.offset >= this.route.__len__():
        this.next_stop = "End of the road!"
        update_gui()
    else:
        this.next_stop = this.route[this.offset][0]
        update_gui()
        copy_waypoint(this.parent)


def journal_entry(cmdr, is_beta, system, station, entry, state):
    if (entry['event'] == 'FSDJump' or entry['event'] == 'Location') and entry["StarSystem"] == this.next_stop:
        update_route()
    elif entry['event'] in ['SupercruiseEntry', 'SupercruiseExit'] and entry['StarSystem'] == this.next_stop:
        update_route()
    elif entry['event'] == 'FSSDiscoveryScan' and entry['SystemName'] == this.next_stop:
        update_route()


def plugin_app(parent):
    this.parent = parent
    this.frame = tk.Frame(parent)
    
    this.waypoint_prev_btn = tk.Button(this.frame, text="^", command=goto_prev_waypoint)
    this.waypoint_btn = tk.Button(this.frame, text=this.next_wp_label + this.next_stop, command=copy_waypoint)
    this.waypoint_next_btn = tk.Button(this.frame, text="v", command=goto_next_waypoint)

    this.upload_route_btn = tk.Button(this.frame, text="Upload new route", command=new_route)
    this.clear_route_btn = tk.Button(this.frame, text="Clear route", command=clear_route)

    this.waypoint_prev_btn.grid(row=0, columnspan=2)
    this.waypoint_btn.grid(row=1, columnspan=2)
    this.waypoint_next_btn.grid(row=2, columnspan=2)
    this.upload_route_btn.grid(row=3, pady=10, padx=0)
    this.clear_route_btn.grid(row=3,column=1)

    this.jumpcounttxt_lbl = tk.Label(this.frame, text=this.jumpcountlbl_txt + str(this.jumps_left))
    this.jumpcounttxt_lbl.grid(row=4, pady=5, sticky=tk.W)

    if not this.route.__len__() > 0:
        this.waypoint_prev_btn.grid_remove()
        this.waypoint_btn.grid_remove()
        this.waypoint_next_btn.grid_remove()
        this.jumpcounttxt_lbl.grid_remove()
        this.clear_route_btn.grid_remove()

    if this.update_available:
        this.update_lbl = tk.Label(this.frame, text="SpanshRouter update available for download!")
        this.update_lbl.grid(row=5, pady=5)

    update_gui()
    
    return this.frame
