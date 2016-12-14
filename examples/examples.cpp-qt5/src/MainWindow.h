/* Copyright (c) 2016  Niklas Rosenstein
 * All rights reserved. */

#pragma once
#include <QtWidgets/QWidget>
#include <QtWidgets/QPushButton>
#include <QtGui/QPixmap>
#include "ui/MainWindow.hpp"

class MainWindow : public QWidget {
  Q_OBJECT;
  Ui_MainWindow ui;
  QPixmap pixmap;

public:
  MainWindow() : QWidget(), pixmap("logo.png") { setupUi(); }

  void setupUi() {
    ui.setupUi(this);
    ui.image->setPixmap(pixmap);
    setWindowTitle("Qt5 Sample Application");

    // Make sure the Close button does what it's supposed to do.
    QPushButton* closeButton = ui.buttonBox->button(QDialogButtonBox::Close);
    connect(closeButton, SIGNAL (clicked()), this, SLOT (close()));
  }

};
