// Independent painter fixture: ordinary/traced pixels must be literally equal.
#include <QImage>
#include <QPainter>
#include <QPainterPath>
#include <cstdio>
int main(int argc,char **argv){
    if(argc!=2)return 2;
    QImage image(1533,1032,QImage::Format_ARGB32_Premultiplied);image.fill(Qt::black);
    QPainter p;if(!p.begin(&image))return 3;
    QTransform t;t.translate(10.25,20.75);t.scale(9.642857142857142,-9.642857142857142);p.setTransform(t);
    p.setRenderHint(QPainter::Antialiasing,false);
    QPen pen(Qt::yellow);pen.setCosmetic(true);pen.setWidthF(1);pen.setCapStyle(Qt::RoundCap);p.setPen(pen);
    p.drawLine(QLineF(10,-10,100,-20));
    QPainterPath path;path.moveTo(20,-30);path.lineTo(40,-10);path.lineTo(60,-30);p.drawPath(path);
    p.fillPath(path,QBrush(Qt::blue));
    p.strokePath(path,pen);
    p.end();
    std::printf("Qt runtime %s\n",qVersion());
    return image.save(argv[1])?0:4;
}
