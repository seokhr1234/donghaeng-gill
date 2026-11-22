package app.donghaeng.gill.demo;

import android.content.Context;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.os.SystemClock;
import android.view.Surface;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

@CapacitorPlugin(name = "DonghaengHeading")
public class HeadingPlugin extends Plugin implements SensorEventListener {
    private SensorManager manager;
    private Sensor rotation;
    private boolean running = false, wanted = false;
    private long lastEvent;
    private final float[] matrix = new float[9], adjusted = new float[9], angles = new float[3];

    @Override public void load() {
        manager = (SensorManager)getContext().getSystemService(Context.SENSOR_SERVICE);
        if (manager != null) rotation = manager.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR);
    }
    @PluginMethod public void start(PluginCall call) {
        getActivity().runOnUiThread(() -> {
            stopSensor();
            if (manager == null || rotation == null) { call.reject("방향 센서를 지원하지 않는 기기예요."); return; }
            wanted = true; running = manager.registerListener(this, rotation, 100000);
            if (!running) { wanted = false; call.reject("방향 센서를 시작하지 못했어요."); return; }
            lastEvent = 0; call.resolve();
        });
    }
    @PluginMethod public void stop(PluginCall call) {
        getActivity().runOnUiThread(() -> { wanted = false; stopSensor(); call.resolve(); });
    }
    private void stopSensor() { running = false; if (manager != null) manager.unregisterListener(this); }
    @Override public void onSensorChanged(SensorEvent event) {
        if (!running || SystemClock.elapsedRealtime() - lastEvent < 90) return;
        lastEvent = SystemClock.elapsedRealtime();
        boolean reliable = event.accuracy != SensorManager.SENSOR_STATUS_UNRELIABLE;
        if (event.values.length > 4 && event.values[4] >= 0 && event.values[4] > Math.PI/4) reliable = false;
        SensorManager.getRotationMatrixFromVector(matrix, event.values);
        int x = SensorManager.AXIS_X, y = SensorManager.AXIS_Y;
        switch (getActivity().getWindowManager().getDefaultDisplay().getRotation()) {
            case Surface.ROTATION_90: x = SensorManager.AXIS_Y; y = SensorManager.AXIS_MINUS_X; break;
            case Surface.ROTATION_180: x = SensorManager.AXIS_MINUS_X; y = SensorManager.AXIS_MINUS_Y; break;
            case Surface.ROTATION_270: x = SensorManager.AXIS_MINUS_Y; y = SensorManager.AXIS_X; break;
        }
        SensorManager.remapCoordinateSystem(matrix, x, y, adjusted);
        SensorManager.getOrientation(adjusted, angles);
        double heading = (Math.toDegrees(angles[0]) + 360) % 360;
        JSObject result = new JSObject(); result.put("degrees", heading); result.put("reliable", reliable);
        notifyListeners("heading", result);
    }
    @Override public void onAccuracyChanged(Sensor sensor, int accuracy) {
        if (running && accuracy == SensorManager.SENSOR_STATUS_UNRELIABLE) {
            JSObject result = new JSObject(); result.put("reliable", false); notifyListeners("heading", result);
        }
    }
    @Override protected void handleOnPause() { stopSensor(); super.handleOnPause(); }
    @Override protected void handleOnResume() {
        super.handleOnResume();
        if (wanted && !running && manager != null && rotation != null) {
            running = manager.registerListener(this, rotation, 100000); lastEvent = 0;
        }
    }
    @Override protected void handleOnDestroy() { wanted = false; stopSensor(); super.handleOnDestroy(); }
}
