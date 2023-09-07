#!/usr/bin/env python

import os
import sys
import sip
import time
import argparse
import subprocess
import threading
import textwrap
try:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *
except:
    sys.exit("PyQt4 not installed.")
try:
    from popplerqt4 import *
    HAS_PDF_SUPPORT=True
except:
    print "Warning: poppler QT4 libraries not detected. PDF support will be disabled."
    HAS_PDF_SUPPORT=False

__author__="You-Wei Cheah"
__version__="0.2"

PRINT_COLON=": "
TEMP_PREFIX="___temp___"
PNG_EXT=".png"
JPEG_EXT=".jpeg"
JPG_EXT=".jpg"
PDF_EXT=".pdf"
TXT_EXT=".txt"
class Vue(QMainWindow):

    def __init__(self,
                 path,
                 verbose,
                 fullscreen,
                 borderless,
                 fontsize,
                 slideshow_delay,
                 cycle_once,
                 parent=None):
        super(Vue, self).__init__(parent)
        self.setWindowTitle('Vue')

        self.path = path
        self.verbose = verbose
        self.use_fade_effects = False
        self.delay = None if slideshow_delay is None else float(slideshow_delay) * 1000
        self.cycle_once = cycle_once
        self.screen = QDesktopWidget().screenGeometry()
        self.w = self.screen.width()
        self.h = self.screen.height()
        self.widget = QWidget(self)
        self.widget.setStyleSheet("background-color:black;")
        self.selected = 0
        self.dict = {}
        self.has_new_img = {}
        self.last_mod = {}
        self.has_valid_extensions = lambda f, b:\
            (f.endswith(JPG_EXT) \
                 or f.endswith(JPEG_EXT) \
                 or f.endswith(PNG_EXT) \
                 or (f.endswith(PDF_EXT) if b else False)) \
                 and not f.startswith(TEMP_PREFIX)
        if self.path:
            self.images = [self.path + f for f in os.listdir(self.path) \
                               if self.has_valid_extensions(f.lower(), HAS_PDF_SUPPORT)]

        self.fontsize = "20" if fontsize is None else fontsize

        self.layout = QStackedLayout(self.widget)
        self.layout.setStackingMode(QStackedLayout.StackAll)

        self.img_label = QLabel(self)
        self.img_label.setFixedSize(QSize(self.w, self.h))
        self.img_label.setAlignment(Qt.AlignCenter)
        self.caption = QLabel(self)
        self.caption.setFixedHeight(self.h/9)
        self.caption.setFixedWidth(self.w-25)
        alignment_widget = QWidget(self)
        alignment_layout = QGridLayout(alignment_widget)
        alignment_layout.addWidget(self.caption, 0, 0, Qt.AlignLeft | Qt.AlignBottom)
        alignment_widget.setStyleSheet("background:transparent;")

        self.layout.addWidget(alignment_widget)
        self.layout.addWidget(self.img_label)
        self.setCentralWidget(self.widget)

        if self.path:
            self.images = [self.path + f for f in os.listdir(self.path) \
                               if self.has_valid_extensions(f.lower(), HAS_PDF_SUPPORT)]
            for img in self.images:
                self.last_mod[img] = os.path.getmtime(img)

        self.current_image = self.images[self.selected]
        print self.current_image
        reader = QImageReader(self.current_image)
        image_size = reader.size()
        image_width = image_size.width()
        image_height = image_size.height()
        w_ratio = float(self.w) / image_width
        h_ratio = float(self.h) / image_height
        if w_ratio > h_ratio:
            reader.setScaledSize(QSize(image_width*h_ratio, self.h))
        else:
            reader.setScaledSize(QSize(self.w, image_height*w_ratio))
        self.image = reader.read()
        self.pixmap = QPixmap(self.image)
        self.setPixmapOnLabel()

        if borderless:
            self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        if fullscreen:
            self.resize(QApplication.desktop().size())
            self.showFullScreen()
        else:
            self.showMaximized()

        if self.delay:
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.next)
            self.timer.start(self.delay)
            self.use_fade_effects = True
            if self.use_fade_effects:
                print "Fade"
                self.createFadeIntermediaries()

        app.exec_()


    def renderToImage(self, page):
        pageSize = page.pageSize()
        page_h = page.pageSizeF().height()
        page_w = page.pageSizeF().width()
        h_ratio = self.h /page_h
        w_ratio = self.w / page_w
        less_dominant_ratio = min(h_ratio, w_ratio)
        default_res = 72
        res = default_res * less_dominant_ratio
        return page.renderToImage(res, res)

    def setCaption(self, caption, opacity=1.0):
        self.caption.setStyleSheet("background-color: rga(0, 0, 0,"+ str(opacity*150) + ");"
                                   "font-size: " + self.fontsize +"pt;"
                                   "color: #fff;"
                                   "qproperty-wordWrap: true;"
                                   "padding: 0px 0px 0px 0px;")
        self.caption.setText(caption)
        self.caption.setAlignment(Qt.AlignCenter)

    def setPixmapOnLabel(self, opacity=1.0):
        pixmap = self.pixmap.scaled(self.w, self.h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        new = QPixmap(pixmap.size())
        new.fill(Qt.transparent)
        painter = QPainter(new)
        painter.setOpacity(opacity)
        painter.drawPixmap(0,0,pixmap)
        painter.end()
        self.img_label.setPixmap(new)

        captions = os.path.dirname(self.current_image) + '/captions/'
        self.current_caption = captions + os.path.basename(self.current_image) + TXT_EXT
        can_set_caption = False
        if os.path.exists(captions) and os.path.exists(self.current_caption):
            can_set_caption = True
        else:
            if self.dict.get(self.current_image, None) is not None:
                self.current_caption = captions + os.path.basename(self.dict.get(self.current_image)) + TXT_EXT
                if os.path.exists(captions) and os.path.exists(self.current_caption):
                    can_set_caption = True

        if not can_set_caption:
            self.caption.hide()
        else:
            f = open(str(self.current_caption), 'r')
            caption = f.read()
            self.setCaption(caption, opacity)
            f.close()
            self.caption.show()

    def getNextImageIndex(self, prevImage=False):
        if prevImage:
            self.next_index = self.selected - 1
            if self.next_index < 0:
                self.next_index = len(self.images) - 1
        else:
            self.next_index = self.selected + 1
            if self.next_index >= len(self.images):
                if self.verbose:
                    print self.__class__.__name__,PRINT_COLON,"Clearing list of images and rereading."
                self.images = [self.path + f for f in os.listdir(self.path) \
                                   if self.has_valid_extensions(f.lower(), HAS_PDF_SUPPORT)]
                for i in range(len(self.images)):
                    new_t = os.path.getmtime(self.images[i])
                    last_t = self.last_mod.get(self.images[i], None)
                    if last_t is not None and new_t != last_t:
                        if self.verbose:
                            print "Update occured."
                        self.last_mod[self.images[i]] = new_t
                    elif self.has_new_img.get(self.images[i], None) is not None:
                        self.images[i] = self.has_new_img.get(self.images[i])

                self.next_index = 0
        return self.next_index

    def fadeLoop(self, i):
        try:
            reader = QImageReader(self.current_image)
            image_size = reader.size()
            image_width = image_size.width()
            image_height = image_size.height()
            w_ratio = float(self.w) / image_width
            h_ratio = float(self.h) / image_height
            if w_ratio > h_ratio:
                reader.setScaledSize(QSize(image_width*h_ratio, self.h))
            else:
                reader.setScaledSize(QSize(self.w, image_height*w_ratio))
            image = reader.read()
            self.pixmap = QPixmap(image)

            self.setPixmapOnLabel(self.opacity[i])
            midpoint = len(self.opacity) / 2
            if i == midpoint:
                self.current_image = self.next_image
            self.loop = QEventLoop(self)
            QTimer.singleShot(50, self.killEventLoop)
            self.loop.exec_()
        except Exception, e:
            print self.opacity[i]
            print e

    def createFadeIntermediaries(self):
        if self.verbose:
            print self.__class__.__name__,PRINT_COLON,"Creating fade intermediaries."
        if self.delay:
            self.opacity = []
            self.max = 1#19
            self.halfway = self.max / 2
            for i in range(self.halfway):
                opacity = round(1.0 - (i*.1), 2)
                self.opacity.append(opacity)

            for i in range(self.halfway, self.max):
                opacity = round(1.0 - (abs(i+1-self.max)*.1), 2)
                self.opacity.append(opacity)

    def next(self, prevImage=False):
        if self.verbose:
            print self.__class__.__name__,PRINT_COLON,"Next invoked."

        self.next_index = self.getNextImageIndex(prevImage)
        self.selected = self.next_index
        if self.cycle_once and self.next_index == 0:
            if self.verbose:
                print self.__class__.__name__,PRINT_COLON,\
                    "Reach end of slideshow and cycle-once argument is",PRINT_COLON,self.cycle_once
            sys.exit(0)
        if os.path.exists(self.images[self.selected]):
            self.next_image = self.images[self.selected]
            if self.next_image.endswith(PDF_EXT):
                # If PDF, render and compress to png so that it'll load faster
                if self.dict.get(self.next_image, None) is None:
                    doc = Poppler.Document.load(self.next_image)
                    doc.setRenderHint(Poppler.Document.Antialiasing)
                    doc.setRenderHint(Poppler.Document.TextAntialiasing)
                    page = doc.page(0)
                    self.ori_name = self.next_image
                    self.image = self.renderToImage(page)
                    self.images[self.selected] = self.path + TEMP_PREFIX + os.path.basename(
                        self.images[self.selected]).replace(PDF_EXT,PNG_EXT)
                    self.image.save(self.images[self.selected],"png",-1)
                    self.next_image = self.images[self.selected]
                    self.new_name = self.next_image
                    self.dict[self.new_name] = self.ori_name
                    self.has_new_img[self.ori_name] = self.new_name
                    sip.delete(page)
                    sip.delete(doc)
            else:
                reader = QImageReader(self.next_image)
                image_size = reader.size()
                image_width = image_size.width()
                image_height = image_size.height()
                w_ratio = float(self.w) / image_width
                h_ratio = float(self.h) / image_height
                if w_ratio > h_ratio:
                    reader.setScaledSize(QSize(image_width*h_ratio, self.h))
                else:
                    reader.setScaledSize(QSize(self.w, image_height*w_ratio))
                self.image = reader.read()
            if self.delay and self.timer.isActive() and self.use_fade_effects:
                for i in range(len(self.opacity)):
                    if self.timer.isActive():
                        self.fadeLoop(i)
                    else:
                        break
            else:
                self.current_image = self.next_image

            self.pixmap = QPixmap(self.image)
            self.setPixmapOnLabel()
            if self.use_fade_effects:
                self.createFadeIntermediaries()
        else:
            # If image is not present, skip to next one in list
            self.next(prevImage)

    def killEventLoop(self):
        self.loop.exit(0)

    def keyPressEvent(self, event):
        if self.verbose:
            print self.__class__.__name__,PRINT_COLON,"Keypress detected."
        key = event.key()
        if key == Qt.Key_Escape:
            self.close()
        elif key == Qt.Key_Left or key == Qt.Key_Right:
            if self.delay:
                self.timer.stop()
            if key == Qt.Key_Left:
                self.next(True)
            if key == Qt.Key_Right:
                self.next()
            if self.delay:
                self.timer.start()

    def removeIntermediaries(self):
        for f in os.listdir(self.path):
            if f.startswith(TEMP_PREFIX):
                os.remove(self.path+f)

    def closeEvent(self, event):
        if self.verbose:
            print self.__class__.__name__,PRINT_COLON,"Close event invoked."
        self.caption.close()
        self.img_label.close()
        self.removeIntermediaries()
        super(Vue, self).closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    parser = argparse.ArgumentParser(
        prog='VUE',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent('''\
         -------------------------------------------------
         VUE is a QT based Python slideshow viewer roughly
         modeled after feh, a imlib2 based image viewer.
         -------------------------------------------------
         Dependencies:
              PyQt 4
              Python 2.7x
         '''))
    parser.add_argument('path', help="Path to read images")
    parser.add_argument('-v ', '--version', action='version',
                        version="Version: %(prog)s {version}".format(version=__version__))
    parser.add_argument('-V', '--verbose', action="store_true", help="Verbose mode")
    parser.add_argument('-F', '--fullscreen', action="store_true", help="Full screen mode")
    parser.add_argument('-x', '--borderless', action="store_true", help="Create borderless display window")
    parser.add_argument('-D', '--slideshow-delay', help="For slideshow mode, wait float seconds between automatically changing slides. Useful for presentations.")
    parser.add_argument('-f', '--fontsize', help="Font size for captions")
    parser.add_argument('--cycle-once', action="store_true", help="Exit after one loop through the slideshow")
    args = parser.parse_args()

    Vue(args.path,
        args.verbose,
        args.fullscreen,
        args.borderless,
        args.fontsize,
        args.slideshow_delay,
        args.cycle_once)
