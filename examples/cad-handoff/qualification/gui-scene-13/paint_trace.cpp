// Observational Qt painter interposition. Original calls are always forwarded unchanged.
// Build with Qt5 development headers, link against the native package's Qt libraries.
#include <QPainter>
#include <QPainterPath>
#include <QPaintDevice>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QFile>
#include <dlfcn.h>
#include <cstdio>
#include <cstdlib>
#include <mutex>
#include <unistd.h>

static thread_local bool observing = false;
static thread_local int forwarding = 0;
struct Forwarding { Forwarding(){++forwarding;} ~Forwarding(){--forwarding;} };
static std::mutex outputMutex;
static unsigned long serial = 0;
static QJsonArray transform(const QTransform &t) {
    return {t.m11(),t.m12(),t.m13(),t.m21(),t.m22(),t.m23(),t.m31(),t.m32(),t.m33()};
}
static QJsonArray color(const QColor &c) { return {c.red(),c.green(),c.blue(),c.alpha()}; }
static QJsonObject brush(const QBrush &b) {
    return {{"style",int(b.style())},{"color",color(b.color())},{"transform",transform(b.transform())}};
}
static QJsonArray pathElements(const QPainterPath &p) {
    QJsonArray a;
    for(int i=0;i<p.elementCount();++i) { auto e=p.elementAt(i);a.append(QJsonArray{int(e.type),e.x,e.y}); }
    return a;
}
static void record(QPainter *p, const char *kind, QJsonObject payload) {
    if(observing || forwarding) return;
    observing=true;
    const char *filename=std::getenv("ICT_PAINT_TRACE");
    QFile epoch("/work/epoch.json");
    if(filename && epoch.open(QIODevice::ReadOnly) && p->device() &&
       p->device()->width()>=1000 && p->device()->height()>=500) {
        auto pen=p->pen(); QJsonArray dashes;
        for(auto d:pen.dashPattern()) dashes.append(d);
        payload.insert("epoch",QJsonDocument::fromJson(epoch.readAll()).object());
        payload.insert("kind",kind);
        payload.insert("painter",QString::number(quintptr(p),16));
        payload.insert("device_address",QString::number(quintptr(p->device()),16));
        payload.insert("device",QJsonArray{p->device()->width(),p->device()->height(),p->device()->devType(),p->device()->devicePixelRatioF()});
        payload.insert("pen",QJsonObject{{"width",pen.widthF()},{"cosmetic",pen.isCosmetic()},
            {"style",int(pen.style())},{"cap",int(pen.capStyle())},{"join",int(pen.joinStyle())},
            {"miter",pen.miterLimit()},{"dash_offset",pen.dashOffset()},{"dashes",dashes},{"brush",brush(pen.brush())}});
        payload.insert("brush",brush(p->brush()));
        payload.insert("world",transform(p->worldTransform()));
        payload.insert("device_transform",transform(p->deviceTransform()));
        payload.insert("window",QJsonArray{p->window().x(),p->window().y(),p->window().width(),p->window().height()});
        payload.insert("viewport",QJsonArray{p->viewport().x(),p->viewport().y(),p->viewport().width(),p->viewport().height()});
        payload.insert("hints",int(p->renderHints()));payload.insert("opacity",p->opacity());
        payload.insert("composition",int(p->compositionMode()));payload.insert("clipping",p->hasClipping());
        payload.insert("clip",pathElements(p->clipPath()));payload.insert("clip_fill",int(p->clipPath().fillRule()));
        payload.insert("background_mode",int(p->backgroundMode()));payload.insert("background",brush(p->background()));
        std::lock_guard<std::mutex> lock(outputMutex);
        payload.insert("serial",double(++serial));
        FILE *f=std::fopen(filename,"ab");
        if(!f) { std::perror("ICT_TRACE_OPEN_FATAL");std::_Exit(91); }
        auto data=QJsonDocument(payload).toJson(QJsonDocument::Compact);
        if(std::fwrite(data.constData(),1,data.size(),f)!=size_t(data.size()) || std::fputc('\n',f)==EOF || std::fclose(f)) std::_Exit(92);
    }
    observing=false;
}
template<class F> static F original(const char *name) {
    void *p=dlsym(RTLD_NEXT,name);
    if(!p) { std::fprintf(stderr,"ICT_TRACE_SYMBOL_FATAL %s %s\n",name,dlerror());std::_Exit(93); }
    return reinterpret_cast<F>(p);
}
void QPainter::drawPath(const QPainterPath &path) {
    static auto call=original<void(*)(QPainter*,const QPainterPath&)>("_ZN8QPainter8drawPathERK12QPainterPath");
    record(this,"path",{{"elements",pathElements(path)},{"fill_rule",int(path.fillRule())}});
    Forwarding scope;call(this,path);
}
void QPainter::drawLines(const QLineF *lines,int count) {
    static auto call=original<void(*)(QPainter*,const QLineF*,int)>("_ZN8QPainter9drawLinesEPK6QLineFi");
    QJsonArray a;for(int i=0;i<count;++i)a.append(QJsonArray{lines[i].x1(),lines[i].y1(),lines[i].x2(),lines[i].y2()});
    record(this,"lines",{{"lines",a}});Forwarding scope;call(this,lines,count);
}
void QPainter::fillPath(const QPainterPath &path,const QBrush &b) {
    static auto call=original<void(*)(QPainter*,const QPainterPath&,const QBrush&)>("_ZN8QPainter8fillPathERK12QPainterPathRK6QBrush");
    record(this,"fill",{{"elements",pathElements(path)},{"fill_rule",int(path.fillRule())},{"fill_brush",brush(b)}});
    Forwarding scope;call(this,path,b);
}
bool QPainter::begin(QPaintDevice *d) {
    static auto call=original<bool(*)(QPainter*,QPaintDevice*)>("_ZN8QPainter5beginEP12QPaintDevice");
    bool success;
    {Forwarding scope;success=call(this,d);}
    if(success) record(this,"begin",{});
    return success;
}
bool QPainter::end() {
    static auto call=original<bool(*)(QPainter*)>("_ZN8QPainter3endEv");
    if(isActive()) record(this,"end",{});
    Forwarding scope;return call(this);
}
