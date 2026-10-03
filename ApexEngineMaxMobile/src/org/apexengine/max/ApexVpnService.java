// language: Java, file: src/org/apexengine/max/ApexVpnService.java
package org.apexengine.max;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Intent;
import android.net.VpnService;
import android.os.Build;
import android.os.ParcelFileDescriptor;
import android.util.Log;

import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.InetSocketAddress;

public class ApexVpnService extends VpnService implements Runnable {

    public static final String ACTION_START = "org.apexengine.max.START";
    public static final String ACTION_STOP  = "org.apexengine.max.STOP";

    private static final String TAG = "ApexVpn";
    private static final String CHANNEL_ID = "apexengine_vpn";
    private static final int NOTIF_ID = 0xA9;

    private Thread worker;
    private ParcelFileDescriptor tunFd;
    private DatagramSocket udp;
    private volatile boolean running = false;

    private String relayHost = "127.0.0.1";
    private int    relayPort = 51820;
    private String dnsPrimary = "1.1.1.1";
    private String dnsSecondary = "1.0.0.1";

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null) {
            String action = intent.getAction();
            if (ACTION_STOP.equals(action)) {
                stopTunnel();
                stopSelf();
                return START_NOT_STICKY;
            }
            if (ACTION_START.equals(action)) {
                relayHost    = intent.getStringExtra("relay_host");
                relayPort    = intent.getIntExtra("relay_port", 51820);
                dnsPrimary   = intent.getStringExtra("dns_primary");
                dnsSecondary = intent.getStringExtra("dns_secondary");
                startTunnel();
                return START_STICKY;
            }
        }
        return START_NOT_STICKY;
    }

    private void startTunnel() {
        if (running) return;
        try {
            Builder b = new Builder();
            b.setSession("ApexEngine");
            b.addAddress("10.99.99.2", 32);
            b.addDnsServer(dnsPrimary == null ? "1.1.1.1" : dnsPrimary);
            if (dnsSecondary != null) b.addDnsServer(dnsSecondary);
            b.addRoute("0.0.0.0", 0);
            b.setMtu(1420);
            if (Build.VERSION.SDK_INT >= 29) b.setMetered(false);
            tunFd = b.establish();
            if (tunFd == null) {
                Log.e(TAG, "TUN establish returned null");
                return;
            }

            udp = new DatagramSocket();
            protect(udp);
            udp.connect(new InetSocketAddress(InetAddress.getByName(relayHost), relayPort));

            running = true;
            worker = new Thread(this, "apex-tunnel");
            worker.start();
            startForegroundNotification();
            Log.i(TAG, "tunnel up: " + relayHost + ":" + relayPort);
        } catch (Exception e) {
            Log.e(TAG, "start error: " + e);
            stopTunnel();
        }
    }

    private void stopTunnel() {
        running = false;
        try { if (worker != null) worker.join(500); } catch (Exception ignored) {}
        try { if (udp != null && !udp.isClosed()) udp.close(); } catch (Exception ignored) {}
        try { if (tunFd != null) tunFd.close(); } catch (Exception ignored) {}
        try { stopForeground(true); } catch (Exception ignored) {}
        Log.i(TAG, "tunnel down");
    }

    @Override
    public void run() {
        try {
            FileInputStream in = new FileInputStream(tunFd.getFileDescriptor());
            FileOutputStream out = new FileOutputStream(tunFd.getFileDescriptor());

            Thread uplink = new Thread(() -> {
                byte[] b = new byte[32768];
                while (running) {
                    try {
                        int n = in.read(b);
                        if (n <= 0) continue;
                        udp.send(new DatagramPacket(b, n));
                    } catch (Exception e) {
                        if (running) Log.w(TAG, "uplink: " + e);
                        break;
                    }
                }
            }, "apex-uplink");

            Thread downlink = new Thread(() -> {
                byte[] r = new byte[65507];
                while (running) {
                    try {
                        DatagramPacket pkt = new DatagramPacket(r, r.length);
                        udp.receive(pkt);
                        out.write(r, 0, pkt.getLength());
                    } catch (Exception e) {
                        if (running) Log.w(TAG, "downlink: " + e);
                        break;
                    }
                }
            }, "apex-downlink");

            uplink.start();
            downlink.start();
            try { uplink.join(); } catch (Exception ignored) {}
            try { downlink.join(); } catch (Exception ignored) {}
        } catch (Exception e) {
            Log.e(TAG, "run error: " + e);
        }
    }

    private void startForegroundNotification() {
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel ch = new NotificationChannel(
                CHANNEL_ID, "ApexEngine Tunnel", NotificationManager.IMPORTANCE_LOW);
            NotificationManager nm = getSystemService(NotificationManager.class);
            if (nm != null) nm.createNotificationChannel(ch);
        }
        Intent open = new Intent(this, getClass());
        int piFlags = Build.VERSION.SDK_INT >= 23 ? PendingIntent.FLAG_IMMUTABLE : 0;
        PendingIntent pi = PendingIntent.getActivity(this, 0, open, piFlags);

        Notification.Builder nb = (Build.VERSION.SDK_INT >= 26)
            ? new Notification.Builder(this, CHANNEL_ID)
            : new Notification.Builder(this);
        nb.setContentTitle("ApexEngine Active")
          .setContentText("UDP tunnel running · VIP features engaged")
          .setSmallIcon(android.R.drawable.stat_sys_download_done)
          .setContentIntent(pi)
          .setOngoing(true);
        startForeground(NOTIF_ID, nb.build());
    }

    @Override
    public void onDestroy() {
        stopTunnel();
        super.onDestroy();
    }
}