#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

import pygtk
pygtk.require("2.0")
import gtk, gtk.glade, gtk.gdk, pango
import dbus, gobject, avahi
from dbus.mainloop.glib import DBusGMainLoop

import uberbus.moodlamp

TYPE = "_moodlamp._udp"
#TODO: Text input for fadetime
t = 0.5
icon = "ml_icon.png"

class UBColorGui(object):
    def __init__(self):
        # Glade setup
        builder = gtk.Builder()
        builder.add_from_file("ubcolorgui.xml")

        self.window = builder.get_object("MainWindow")
        self.lampchooser = builder.get_object("lampChooser")
        self.statusbar = builder.get_object("statusBar")
        self.colorchooser = builder.get_object("colorChooser")
        self.code = builder.get_object("textCode")
        self.codeRunButton = builder.get_object("buttonRun")

        self.colorchooser.connect("color_changed",self.new_color)
        self.codeRunButton.connect("clicked", self.run_code)

        self.code.modify_font(pango.FontDescription('monospace 10'))

        self.status = {'connection': None, 'color': None}
        self.status['connection'] = self.statusbar.get_context_id("connection status")
        self.status['color'] = self.statusbar.get_context_id("color")

        self.lampstore = gtk.ListStore(gobject.TYPE_STRING)
        self.lampchooser.set_model(self.lampstore)

        cell = gtk.CellRendererText()
        self.lampchooser.pack_start(cell)
        self.lampchooser.add_attribute(cell, 'text', 0)

        self.window.connect("delete_event", gtk.main_quit)

        self.window.show_all()

        self.set_status("connection", "0 lamps found")

        # dbus & avahi set up
        loop = DBusGMainLoop()
        bus = dbus.SystemBus(mainloop=loop)
        self.server = dbus.Interface(bus.get_object(avahi.DBUS_NAME, '/'), 'org.freedesktop.Avahi.Server')
        sbrowser = dbus.Interface(bus.get_object(avahi.DBUS_NAME,
            self.server.ServiceBrowserNew(avahi.IF_UNSPEC,
                avahi.PROTO_UNSPEC, TYPE, 'local', dbus.UInt32(0))),
            avahi.DBUS_INTERFACE_SERVICE_BROWSER)
        sbrowser.connect_to_signal("ItemNew", self.moodlamp_found)

    def set_status(self, mid, status):
        if mid not in self.status:
            raise ValueError("Wrong/impossible status")
        self.statusbar.pop(self.status[mid])
        self.status[mid] = self.statusbar.push(self.status[mid], status)
        return self.status[mid]

    def moodlamp_found(self, interface, protocol, name, stype, domain, flags):
        """Called when avahi found some service"""
        # need to resolve it. enterprisy api, no doubt
        self.server.ResolveService(interface, protocol, name, stype,
            domain, avahi.PROTO_UNSPEC, dbus.UInt32(0),
            reply_handler=self.moodlamp_resolved, error_handler=self.resolve_error)

    def moodlamp_resolved(self, *args):
        """Called when a new lamp was found"""
        self.lampchooser.append_text("%s.local" % args[2])
        self.set_status("connection",
                "%d lamps found" % len(self.lampchooser.get_model()))

    def resolve_error(self, *args):
        """Called when Avahi tries to resolve the service and fails"""
        self.set_status("connection", "Error resolving moodlamp")

    def run_code(self, widget):
        buf = self.code.get_buffer()
        code = buf.get_text(buf.get_start_iter(), buf.get_end_iter())
        # insecure, don't try this at home kids ;)
        c = compile(code, '<string>', 'exec')
        eval(c, {'fadecolor': self.fade_color, 'setcolor': self.set_color})

    def lamp_cb(self, callback):
        model = self.lampchooser.get_model()
        index = self.lampchooser.get_active()
        if index:
            lamp = model[index][0]
            s = uberbus.moodlamp.Moodlamp(lamp, True)
            s.connect()
            callback(s)
            s.disconnect()

    def fade_color(self, r, g, b, t):
        print "Fade color to 0x%x%x%x" % (r, g, b)
        self.set_status('color', "Fade to 0x%x%x%x" % (r, g, b))
        self.lamp_cb(
            lambda s: s.timedfade(r, g, b, t))

    def set_color(self, r, g, b):
        print "Set color to 0x%x%x%x" % (r, g, b)
        self.set_status('color', "Set to 0x%x%x%x" % (r, g, b))
        self.lamp_cb(
            lambda s: s.setcolor(r, g, b))

    def new_color(self, color):
        c = color.get_current_color()
        self.fade_color(c.red/256, c.green/256, c.blue/256, 0.5)

def main():
    bcb = UBColorGui()
    gtk.main()

if __name__== "__main__":
    main()
