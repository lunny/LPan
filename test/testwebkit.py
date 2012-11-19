import gtk
import webkit
view = webkit.WebView()
sw = gtk.ScrolledWindow()
sw.add(view)
win = gtk.Window(gtk.WINDOW_TOPLEVEL)
win.add(sw)
win.show_all()
view.open("http://w3.org/")
gtk.main()