#!/usr/bin/python
import pygtk
pygtk.require("2.0")

import gtk, gtk.glade, gtk.gdk, pango
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

        self.window        = self.wtree.get_widget("MainWindow")
        self.lampchooser   = self.wtree.get_widget("lampChooser")
        self.statusbar     = self.wtree.get_widget("statusBar")
        self.colorchooser  = self.wtree.get_widget("colorChooser")
        self.code          = self.wtree.get_widget("textCode")
        self.codeRunButton = self.wtree.get_widget("buttonRun")
        self.colorchooser.connect("color_changed",self.new_color)
        self.codeRunButton.connect("clicked", self.run_code)

        self.code.modify_font(pango.FontDescription('monospace 10'))

        self.status = {'connection': None, 'color': None}
        self.status['connection'] = self.statusbar.get_context_id("connection status")
        self.status['color'] = self.statusbar.get_context_id("color")

        self.lampstore    = gtk.ListStore(gobject.TYPE_STRING)
        self.lampchooser.set_model(self.lampstore)

        cell = gtk.CellRendererText()
        self.lampchooser.pack_start(cell)
        self.lampchooser.add_attribute(cell, 'text', 0)

        self.window.connect("delete_event", gtk.main_quit)

        self.window.show_all()

        self.set_status("connection", "0 lamps found")
        loop = DBusGMainLoop()
        bus = dbus.SystemBus(mainloop=loop)
        self.server = dbus.Interface(bus.get_object(avahi.DBUS_NAME, '/'), 'org.freedesktop.Avahi.Server')
        sbrowser = dbus.Interface(bus.get_object(avahi.DBUS_NAME,
            self.server.ServiceBrowserNew(avahi.IF_UNSPEC,
                avahi.PROTO_UNSPEC, TYPE, 'local', dbus.UInt32(0))),
            avahi.DBUS_INTERFACE_SERVICE_BROWSER)
        sbrowser.connect_to_signal("ItemNew", self.mlfound)

    def set_status(self, mid, status):
        if mid not in self.status:
            raise ValueError
        self.statusbar.pop(self.status[mid])
        self.status[mid] = self.statusbar.push(self.status[mid], status)
        return self.status[mid]

    def mlfound(self, interface, protocol, name, stype, domain, flags):
        print "Found service '%s' type '%s' domain '%s' " % (name, stype, domain)

        self.server.ResolveService(interface, protocol, name, stype,
            domain, avahi.PROTO_UNSPEC, dbus.UInt32(0),
            reply_handler=self.service_resolved, error_handler=self.print_error)

    def service_resolved(self, *args):
        print 'service resolved'
        print 'name:', args[2]
        self.lampchooser.append_text("%s.local" % args[2])
        self.set_status("connection", "%d lamps found" %
                len(self.lampchooser.get_model()))
#        print 'address:', args[7]
#        print 'port:', args[8]

    def print_error(self, *args):
        print 'error_handler'
        print args[0]

    def run_code(self, widget):
        buf = self.code.get_buffer()
        code = buf.get_text(buf.get_start_iter(), buf.get_end_iter())
        c = compile(code, '<string>', 'exec')
        eval(c, {'fadecolor': self.fade_color, 'setcolor': self.set_color})

    def lamp_cb(self, cb):
        model = self.lampchooser.get_model()
        index = self.lampchooser.get_active()
        if index:
            lamp = model[index][0]
            s = uberbus.moodlamp.Moodlamp(lamp, True)
            s.connect()
            cb(s)
            s.disconnect()

    def fade_color(self, r, g, b, t):
        print "Fade color to 0x%x%x%x" % (r,g,b)
        self.lamp_cb(
            lambda s: s.timedfade(r,g,b,t))

    def set_color(self, r, g, b):
        print "Set color to 0x%x%x%x" % (r,g,b)
        self.lamp_cb(
            lambda s: s.setcolor(r,g,b))

    def new_color(self, color):
        c = color.get_current_color()
        self.fade_color(c.red/256, c.green/256, c.blue/256, 0.5)

def main():
    loop = DBusGMainLoop()
    bcb = UBColorGui(loop)
    gtk.main()

if __name__== "__main__":
    main()
