
package com.example.tkclient;

import javax.swing.*;
import java.awt.*;

public class SemaphoreIndicator extends JComponent {
    private Color color = Color.GRAY;

    public void setState(String state) {
        switch (state) {
            case "green" -> color = new Color(0x16,0xa3,0x4a);
            case "orange" -> color = new Color(0xf5,0x9e,0x0b);
            case "red" -> color = new Color(0xef,0x44,0x44);
            default -> color = Color.GRAY;
        }
        repaint();
    }

    @Override
    public Dimension getPreferredSize() {
        return new Dimension(20,20);
    }

    @Override
    protected void paintComponent(Graphics g) {
        super.paintComponent(g);
        int d = Math.min(getWidth(), getHeight()) - 4;
        g.setColor(color);
        g.fillOval(2,2,d,d);
        g.setColor(Color.DARK_GRAY);
        g.drawOval(2,2,d,d);
    }
}
