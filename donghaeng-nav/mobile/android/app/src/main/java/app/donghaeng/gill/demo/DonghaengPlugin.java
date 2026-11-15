package app.donghaeng.gill.demo;

import android.app.AlertDialog;
import android.content.Context;
import android.content.SharedPreferences;
import android.text.InputType;
import android.widget.EditText;
import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import org.json.JSONObject;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.*;

@CapacitorPlugin(name = "Donghaeng")
public class DonghaengPlugin extends Plugin {
    private final ExecutorService pool = Executors.newFixedThreadPool(2);
    private final Map<String,HttpURLConnection> connections = new ConcurrentHashMap<>();
    private final Set<String> active = ConcurrentHashMap.newKeySet(), cancelled = ConcurrentHashMap.newKeySet();
    private final Semaphore slots = new Semaphore(2);
    private SharedPreferences prefs;
    private final Set<String> backendPaths = new HashSet<>(Arrays.asList("/api/status","/api/analyze-condition","/api/select-route","/api/routes/city-walk","/api/city/coverage","/api/coverage","/api/features","/api/places","/api/routes/walk"));
    @Override public void load() { prefs = getContext().getSharedPreferences("donghaeng-demo", Context.MODE_PRIVATE); }
    private String key() { return prefs.getString("odsayKey", BuildConfig.ODSAY_ANDROID_KEY).trim(); }
    private synchronized int used(boolean increment) {
        SimpleDateFormat f = new SimpleDateFormat("yyyy-MM-dd", Locale.ROOT); f.setTimeZone(TimeZone.getTimeZone("Asia/Seoul"));
        String day = f.format(new Date()); int value = day.equals(prefs.getString("day", "")) ? prefs.getInt("used",0) : 0;
        if (increment && value < 20) prefs.edit().putString("day",day).putInt("used",++value).apply();
        return value;
    }
    @PluginMethod public void status(PluginCall call) { JSObject r = new JSObject(); r.put("configured",!key().isEmpty()); r.put("used",used(false)); r.put("dailyLimit",20); call.resolve(r); }
    @PluginMethod public void configureKey(PluginCall call) {
        getActivity().runOnUiThread(() -> {
            EditText input = new EditText(getContext()); input.setSingleLine(true); input.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
            input.setHint("ODsay Android용 키");
            new AlertDialog.Builder(getActivity()).setTitle("시연용 교통 키 설정")
                .setMessage("ODsay에 등록한 Android 키를 입력하세요. 이 기기의 앱 설정에 저장합니다. 서버용 키에는 IP 제한이 적용됩니다.")
                .setView(input).setPositiveButton("저장",(dialog,which) -> {
                    String value=input.getText().toString().trim();
                    if(value.length()>1024 || value.contains("\n") || value.contains("\r")){call.reject("키 입력 형식을 확인해 주세요.");return;}
                    prefs.edit().putString("odsayKey",value).apply(); input.setText(""); JSObject r=new JSObject();r.put("configured",!value.isEmpty());call.resolve(r);
                }).setNegativeButton("취소",(dialog,which) -> call.resolve()).setNeutralButton("키 삭제",(dialog,which) -> {prefs.edit().putString("odsayKey","").apply();call.resolve();}).show();
        });
    }
    @PluginMethod public void cancel(PluginCall call) {
        String id=call.getString("requestId",""); if(active.contains(id))cancelled.add(id); HttpURLConnection c=connections.get(id);if(c!=null)c.disconnect();call.resolve();
    }
    private void result(PluginCall call,int status,String body){JSObject r=new JSObject();r.put("status",status);r.put("body",body);call.resolve(r);}
    private String failure(String code,String message){return new JSObject().put("code",code).put("error",message).toString();}
    private String exchange(String id,URL url,String method,String body) throws Exception {
        if(cancelled.contains(id))throw new InterruptedIOException();
        HttpURLConnection c=(HttpURLConnection)url.openConnection();connections.put(id,c);
        try {
            c.setInstanceFollowRedirects(false);c.setConnectTimeout(12000);c.setReadTimeout(15000);c.setRequestMethod(method);
            c.setRequestProperty("Accept","application/json");c.setRequestProperty("User-Agent","Donghaeng-Android-Demo/1.0");
            if(cancelled.contains(id))throw new InterruptedIOException();
            if("POST".equals(method)){c.setDoOutput(true);c.setRequestProperty("Content-Type","application/json; charset=utf-8");try(OutputStream out=c.getOutputStream()){out.write(body.getBytes(StandardCharsets.UTF_8));}}
            int status=c.getResponseCode();if(status>=300&&status<400)throw new IOException();
            InputStream stream=status>=400?c.getErrorStream():c.getInputStream();if(stream==null)throw new IOException();
            ByteArrayOutputStream data=new ByteArrayOutputStream();byte[] buffer=new byte[8192];int count;
            try(InputStream in=stream){while((count=in.read(buffer))!=-1){if(cancelled.contains(id)||data.size()+count>2500000)throw new IOException();data.write(buffer,0,count);}}
            return new JSObject().put("status",status).put("body",data.toString("UTF-8")).toString();
        }finally{connections.remove(id);c.disconnect();}
    }
    private void execute(PluginCall call,boolean search) {
        String id=call.getString("requestId","");if(!id.matches("[a-zA-Z0-9]{1,64}")||!slots.tryAcquire()){result(call,429,failure("android_busy","다른 요청을 처리하고 있어요."));return;}
        active.add(id);
        pool.execute(() -> {
            try {
                URL url;String method,body="";
                if(search){
                    String token=key();if(token.isEmpty()){result(call,503,failure("android_key_missing","오른쪽 위 교통 키에서 ODsay Android 키를 설정해 주세요."));return;}
                    JSArray a=call.getArray("origin"),b=call.getArray("destination");if(a==null||b==null||a.length()!=2||b.length()!=2)throw new IllegalArgumentException();
                    double ay=a.getDouble(0),ax=a.getDouble(1),by=b.getDouble(0),bx=b.getDouble(1);
                    if(!Double.isFinite(ay)||!Double.isFinite(ax)||!Double.isFinite(by)||!Double.isFinite(bx)||Math.abs(ay)>90||Math.abs(by)>90||Math.abs(ax)>180||Math.abs(bx)>180)throw new IllegalArgumentException();
                    synchronized(this){if(used(false)>=20){result(call,429,failure("android_daily_limit","이 기기의 오늘 교통 검색 한도에 도달했어요."));return;}used(true);}
                    url=new URL("https://api.odsay.com/v1/api/searchPubTransPathT?apiKey="+URLEncoder.encode(token,"UTF-8")+"&SX="+ax+"&SY="+ay+"&EX="+bx+"&EY="+by+"&OPT=0&output=json");method="GET";
                }else{
                    String path=call.getString("path","");URI part=new URI(path);method=call.getString("method","GET");body=call.getString("body","");
                    if(!path.startsWith("/api/")||part.isAbsolute()||part.getRawAuthority()!=null||part.getFragment()!=null||!backendPaths.contains(part.getPath())||!Arrays.asList("GET","POST").contains(method)||body.getBytes(StandardCharsets.UTF_8).length>32768)throw new IllegalArgumentException();
                    url=new URL("https://donghaeng-gill.vercel.app"+path);
                }
                JSONObject data=new JSONObject(exchange(id,url,method,body));int status=data.getInt("status");String content=data.getString("body");
                if(search){
                    JSONObject raw=new JSONObject(content);
                    if(raw.has("error")){
                        Object e=raw.get("error");JSONObject detail=e instanceof org.json.JSONArray?((org.json.JSONArray)e).optJSONObject(0):e instanceof JSONObject?(JSONObject)e:new JSONObject();
                        String code=detail==null?"":detail.optString("code","");if(!code.matches("-?\\d{1,4}"))code="";
                        String msg=detail==null?"":detail.optString("message",detail.optString("msg",""));
                        String safe=msg.toLowerCase(Locale.ROOT).matches(".*(auth|apikey|api key|인증).*" )?"API key authentication":"provider error";
                        content=new JSONObject().put("error",new JSONObject().put("code",code).put("message",safe)).toString();
                    }
                }
                if(cancelled.contains(id)){result(call,499,failure("cancelled","요청을 취소했어요."));return;}
                result(call,status,content);
            }catch(IllegalArgumentException e){result(call,400,failure("invalid_android_request","요청 형식을 확인해 주세요."));}
            catch(Exception e){result(call,cancelled.contains(id)?499:503,failure("android_connection_failed","연결에 실패했어요. 교통 키와 인터넷 연결을 확인해 주세요."));}
            finally{connections.remove(id);active.remove(id);cancelled.remove(id);slots.release();}
        });
    }
    @PluginMethod public void search(PluginCall call){execute(call,true);}
    @PluginMethod public void backend(PluginCall call){execute(call,false);}
    @Override protected void handleOnDestroy(){for(HttpURLConnection c:connections.values())c.disconnect();pool.shutdownNow();super.handleOnDestroy();}
}
