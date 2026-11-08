// Replay recorded painter primitives in the same native Qt runtime, without CAD imports.
// Input is a bounded numeric stream produced from the retained JSON trace by replay_input.py.
#include <QPainter>
#include <QPainterPath>
#include <QImage>
#include <fstream>
#include <stdexcept>
#include <iostream>
static std::ifstream input;
static double number(){double v;if(!(input>>v))throw std::runtime_error("Truncated numeric replay");return v;}
static int integer(){double v=number();if(v!=int(v))throw std::runtime_error("Noninteger");return int(v);}
static QTransform transform(){double a[9];for(auto &v:a)v=number();return QTransform(a[0],a[1],a[2],a[3],a[4],a[5],a[6],a[7],a[8]);}
static QColor color(){int r=integer(),g=integer(),b=integer(),a=integer();return QColor(r,g,b,a);}
static QBrush brush(){int style=integer();auto c=color();auto t=transform();if(style<0||style>14)throw std::runtime_error("Unsupported gradient/texture");QBrush b(c,Qt::BrushStyle(style));b.setTransform(t);return b;}
static QPainterPath path(){
    int count=integer(),fill=integer();if(count<0||count>100000)throw std::runtime_error("Path bound");
    QPainterPath p;p.setFillRule(Qt::FillRule(fill));
    for(int i=0;i<count;++i){int type=integer();double x=number(),y=number();
        if(type==0)p.moveTo(x,y);else if(type==1)p.lineTo(x,y);
        else if(type==2 && i+2<count){int t2=integer();double x2=number(),y2=number();int t3=integer();double x3=number(),y3=number();
            if(t2!=3||t3!=3)throw std::runtime_error("Invalid cubic");p.cubicTo(x,y,x2,y2,x3,y3);i+=2;}
        else throw std::runtime_error("Invalid element");}
    return p;
}
int main(int argc,char **argv){try{
    if(argc!=3)return 2;input.open(argv[1]);int width=integer(),height=integer(),count=integer();
    if(width!=1533||height!=1032||count<1||count>100000)throw std::runtime_error("Replay dimensions/count");
    QImage image(width,height,QImage::Format_ARGB32_Premultiplied);image.fill(Qt::black);QPainter p(&image);
    for(int i=0;i<count;++i){int kind=integer();p.save();p.setWorldTransform(transform());
        int hints=integer();p.setRenderHints(QPainter::RenderHints(0x7f),false);p.setRenderHints(QPainter::RenderHints(hints),true);
        p.setOpacity(number());p.setCompositionMode(QPainter::CompositionMode(integer()));
        double width=number();bool cosmetic=integer();int style=integer(),cap=integer(),join=integer();double miter=number(),offset=number();
        int n=integer();QVector<qreal>dashes;for(int j=0;j<n;++j)dashes.append(number());
        QPen pen;pen.setBrush(brush());pen.setWidthF(width);pen.setCosmetic(cosmetic);pen.setStyle(Qt::PenStyle(style));
        pen.setCapStyle(Qt::PenCapStyle(cap));pen.setJoinStyle(Qt::PenJoinStyle(join));pen.setMiterLimit(miter);
        if(!dashes.isEmpty())pen.setDashPattern(dashes);pen.setDashOffset(offset);p.setPen(pen);p.setBrush(brush());
        p.setBackgroundMode(Qt::BGMode(integer()));p.setBackground(brush());bool clip=integer();auto clipping=path();
        if(clip)p.setClipPath(clipping);else p.setClipping(false);
        if(kind==0){int n=integer();QVector<QLineF>lines;for(int j=0;j<n;++j){double x1=number(),y1=number(),x2=number(),y2=number();lines.append(QLineF(x1,y1,x2,y2));}p.drawLines(lines);}
        else if(kind==1){auto v=path();p.drawPath(v);}
        else if(kind==2){auto v=path();p.fillPath(v,brush());}else throw std::runtime_error("Invalid primitive");
        p.restore();
    }
    double trailing;if(input>>trailing)throw std::runtime_error("Extra replay tokens");p.end();
    if(!image.save(argv[2]))throw std::runtime_error("Cannot save");std::cout<<"Qt runtime "<<qVersion()<<"; calls "<<count<<"\n";
    return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<"\n";return 1;}}
