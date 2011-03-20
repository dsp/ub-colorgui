#!/usr/bin/python
import pygtk
pygtk.require("2.0")

import gtk, gtk.glade, gtk.gdk
import sys
import dbus, gobject, avahi
from dbus.mainloop.glib import DBusGMainLoop
import uberbus.moodlamp

TYPE = "_moodlamp._udp"
#TODO: Text input for fadetime
t = 0.5
icon = "./ml_icon.png"
#TODO: Autodetect lamps using avahi
#lamps = ["alle.local", "moon.local", "spot.local", "oben.local", "unten.local"]

class UBColorGui:
    def __init__(self, loop):
        # GLADE SETUP
        self.wtree = gtk.glade.XML("ubcolorgui.glade", "MainWindow")

        self.window       = self.wtree.get_widget("MainWindow")
        self.lampchooser  = self.wtree.get_widget("lampChooser")
        self.colorchooser = self.wtree.get_widget("colorChooser")
        self.colorchooser.connect("color_changed",self.new_color)

        self.lampstore    = gtk.ListStore(gobject.TYPE_STRING)
        self.lampchooser.set_model(self.lampstore)

        cell = gtk.CellRendererText()
        self.lampchooser.pack_start(cell)
        self.lampchooser.add_attribute(cell, 'text', 0)

        self.window.connect("delete_event", gtk.main_quit)

        self.window.show_all()

        loop = DBusGMainLoop()
        bus = dbus.SystemBus(mainloop=loop)
        self.server = dbus.Interface(bus.get_object(avahi.DBUS_NAME, '/'), 'org.freedesktop.Avahi.Server')
        sbrowser = dbus.Interface(bus.get_object(avahi.DBUS_NAME,
            self.server.ServiceBrowserNew(avahi.IF_UNSPEC,
                avahi.PROTO_UNSPEC, TYPE, 'local', dbus.UInt32(0))),
            avahi.DBUS_INTERFACE_SERVICE_BROWSER)
        sbrowser.connect_to_signal("ItemNew", self.mlfound)

    def mlfound(self, interface, protocol, name, stype, domain, flags):
        print "Found service '%s' type '%s' domain '%s' " % (name, stype, domain)

        self.server.ResolveService(interface, protocol, name, stype,
            domain, avahi.PROTO_UNSPEC, dbus.UInt32(0),
            reply_handler=self.service_resolved, error_handler=self.print_error)

    def service_resolved(self, *args):
        print 'service resolved'
        print 'name:', args[2]
        self.lampchooser.append_text("%s.local" % args[2])
#        print 'address:', args[7]
#        print 'port:', args[8]

    def print_error(self, *args):
        print 'error_handler'
        print args[0]

    def new_color(self, color):
        model = self.lampchooser.get_model()
        index = self.lampchooser.get_active()
        if index:
            lamp = model[index][0]
            print "Active lamp: %s" % lamp
            s = uberbus.moodlamp.Moodlamp(lamp, True)
            c = color.get_current_color()
            r = c.red/256;
            g = c.green/256;
            b = c.blue/256;
            s.connect()
            s.timedfade(r,g,b,t)
            print "Setting %s to %s%s%s" % (lamp, hex(r)[2:], hex(g)[2:], hex(b)[2:])
            s.disconnect()

def main():
    loop = DBusGMainLoop()
    bcb = UBColorGui(loop)
    gtk.main()

if __name__== "__main__":
    main()
