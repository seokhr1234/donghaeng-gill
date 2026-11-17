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
    private String geminiKey() { return prefs.getString("geminiKey", "").trim(); }
    private JSObject settings() {
        JSObject r = new JSObject(); r.put("configured", !key().isEmpty()); r.put("used", used(false)); r.put("dailyLimit", 20);
        r.put("keySource", prefs.contains("odsayKey") ? (key().isEmpty() ? "disabled" : "device") : (key().isEmpty() ? "missing" : "bundled"));
        r.put("bundledKeyAvailable", !BuildConfig.ODSAY_ANDROID_KEY.trim().isEmpty());
        r.put("geminiConfigured", !geminiKey().isEmpty()); return r;
    }
    private JSObject changedSettings() { JSObject r=settings(); r.put("changed",true); return r; }
    private synchronized int used(boolean increment) {
        SimpleDateFormat f = new SimpleDateFormat("yyyy-MM-dd", Locale.ROOT); f.setTimeZone(TimeZone.getTimeZone("Asia/Seoul"));
        String day = f.format(new Date()); int value = day.equals(prefs.getString("day", "")) ? prefs.getInt("used",0) : 0;
        if (increment && value < 20) prefs.edit().putString("day",day).putInt("used",++value).apply();
        return value;
    }
    @PluginMethod public void status(PluginCall call) { call.resolve(settings()); }
    @PluginMethod public void resetKey(PluginCall call) { prefs.edit().remove("odsayKey").apply(); call.resolve(changedSettings()); }
    @PluginMethod public void clearGemini(PluginCall call) { prefs.edit().remove("geminiKey").apply(); call.resolve(changedSettings()); }
    @PluginMethod public void configureGemini(PluginCall call) {
        getActivity().runOnUiThread(() -> {
            EditText input = new EditText(getContext()); input.setSingleLine(true);
            input.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD | InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS);
            input.setHint("Gemini API 키");
            String message = geminiKey().isEmpty() ? "개인 Gemini 키를 입력하면 이 기기에 저장하고 Google에 직접 연결합니다. 입력하지 않으면 기존 Vercel 서버 연결을 사용합니다." : "기기에 Gemini 키가 저장되어 있습니다. 보안을 위해 입력란은 비워 둡니다. 변경할 때만 새 키를 입력하세요.";
            new AlertDialog.Builder(getActivity()).setTitle("Gemini API 키 입력").setMessage(message)
                .setView(input).setPositiveButton("저장", (dialog, which) -> {
                    String value = input.getText().toString().trim();
                    if (!value.matches("[-A-Za-z0-9_.]{20,300}")) {input.setText(""); call.reject("Gemini 키 값만 입력해 주세요. 기존 설정은 유지됩니다."); return;}
                    prefs.edit().putString("geminiKey", value).apply(); input.setText(""); call.resolve(changedSettings());
                }).setNegativeButton("취소", (dialog, which) -> call.resolve(settings())).show();
        });
    }
    @PluginMethod public void configureKey(PluginCall call) {
        getActivity().runOnUiThread(() -> {
            EditText input = new EditText(getContext()); input.setSingleLine(true); input.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
            input.setHint("ODsay Android용 키");
            new AlertDialog.Builder(getActivity()).setTitle("시연용 교통 키 설정")
                .setMessage(key().isEmpty() ? (BuildConfig.ODSAY_ANDROID_KEY.trim().isEmpty() ? "공개 배포판에는 교통 키를 내장하지 않습니다. 본인의 ODsay Android 키를 입력하면 이 기기에 저장합니다." : "현재 교통 키가 비어 있습니다. 새 Android 키를 입력하거나 API 설정에서 내장 키를 복원하세요.") : "현재 교통 키가 적용되어 있습니다. 보안을 위해 입력란은 비워 둡니다. 변경할 때만 새 Android 키를 입력하세요.")
                .setView(input).setPositiveButton("저장",(dialog,which) -> {
                    String value=input.getText().toString().trim();
                    if(value.isEmpty() || value.length()>1024 || value.contains("\n") || value.contains("\r")){call.reject("새 키를 입력하거나 취소해 주세요. 기존 설정은 유지됩니다.");return;}
                    prefs.edit().putString("odsayKey",value).apply(); input.setText(""); call.resolve(changedSettings());
                }).setNegativeButton("취소",(dialog,which) -> call.resolve()).setNeutralButton("키 삭제",(dialog,which) -> {prefs.edit().putString("odsayKey","").apply();call.resolve(changedSettings());}).show();
        });
    }
    @PluginMethod public void cancel(PluginCall call) {
        String id=call.getString("requestId",""); if(active.contains(id))cancelled.add(id); HttpURLConnection c=connections.get(id);if(c!=null)c.disconnect();call.resolve();
    }
    private void result(PluginCall call,int status,String body){JSObject r=new JSObject();r.put("status",status);r.put("body",body);call.resolve(r);}
    private String failure(String code,String message){return new JSObject().put("code",code).put("error",message).toString();}
    private String exchange(String id,URL url,String method,String body,String googleKey) throws Exception {
        if(cancelled.contains(id))throw new InterruptedIOException();
        HttpURLConnection c=(HttpURLConnection)url.openConnection();connections.put(id,c);
        try {
            c.setInstanceFollowRedirects(false);c.setConnectTimeout(12000);c.setReadTimeout(15000);c.setRequestMethod(method);
            c.setRequestProperty("Accept","application/json");c.setRequestProperty("User-Agent","Donghaeng-Android-Demo/1.0");
            if(googleKey!=null)c.setRequestProperty("x-goog-api-key",googleKey);
            if(cancelled.contains(id))throw new InterruptedIOException();
            if("POST".equals(method)){c.setDoOutput(true);c.setRequestProperty("Content-Type","application/json; charset=utf-8");try(OutputStream out=c.getOutputStream()){out.write(body.getBytes(StandardCharsets.UTF_8));}}
            int status=c.getResponseCode();if(status>=300&&status<400)throw new IOException();
            InputStream stream=status>=400?c.getErrorStream():c.getInputStream();if(stream==null)throw new IOException();
            ByteArrayOutputStream data=new ByteArrayOutputStream();byte[] buffer=new byte[8192];int count;
            try(InputStream in=stream){while((count=in.read(buffer))!=-1){if(cancelled.contains(id)||data.size()+count>2500000)throw new IOException();data.write(buffer,0,count);}}
            return new JSObject().put("status",status).put("body",data.toString("UTF-8")).toString();
        }finally{connections.remove(id);c.disconnect();}
    }
    private void execute(PluginCall call,boolean search,boolean gemini) {
        String id=call.getString("requestId","");if(!id.matches("[a-zA-Z0-9]{1,64}")||!slots.tryAcquire()){result(call,429,failure("android_busy","다른 요청을 처리하고 있어요."));return;}
        active.add(id);
        pool.execute(() -> {
            try {
                URL url;String method,body="",googleKey=null;
                if(gemini){
                    googleKey=geminiKey();if(googleKey.isEmpty()){result(call,503,failure("android_gemini_key_missing","Gemini 키를 API 설정에서 입력해 주세요."));return;}
                    String model=call.getString("model","");JSObject request=call.getObject("request");
                    if(!model.matches("gemini-[a-z0-9.-]{1,80}")||request==null)throw new IllegalArgumentException();
                    body=request.toString();if(body.getBytes(StandardCharsets.UTF_8).length>65536)throw new IllegalArgumentException();
                    url=new URL("https://generativelanguage.googleapis.com/v1beta/models/"+model+":generateContent");method="POST";
                }else if(search){
                    String token=key();if(token.isEmpty()){result(call,503,failure("android_key_missing","오른쪽 위 API 설정에서 ODsay Android 키를 입력해 주세요."));return;}
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
                JSONObject data=new JSONObject(exchange(id,url,method,body,googleKey));int status=data.getInt("status");String content=data.getString("body");
                if(gemini && status>=400)content=failure(status==429?"gemini_quota":"gemini_connection_failed",status==429?"Gemini 사용 한도에 도달했어요.":"Gemini 키와 모델 설정을 확인해 주세요.");
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
            catch(Exception e){result(call,cancelled.contains(id)?499:503,failure("android_connection_failed",gemini?"Gemini 연결에 실패했어요. API 설정과 인터넷 연결을 확인해 주세요.":"연결에 실패했어요. 교통 키와 인터넷 연결을 확인해 주세요."));}
            finally{connections.remove(id);active.remove(id);cancelled.remove(id);slots.release();}
        });
    }
    @PluginMethod public void search(PluginCall call){execute(call,true,false);}
    @PluginMethod public void backend(PluginCall call){execute(call,false,false);}
    @PluginMethod public void gemini(PluginCall call){execute(call,false,true);}
    @Override protected void handleOnDestroy(){for(HttpURLConnection c:connections.values())c.disconnect();pool.shutdownNow();super.handleOnDestroy();}
}
