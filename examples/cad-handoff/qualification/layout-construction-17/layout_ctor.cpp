// Authored diagnostic only: forward the installed constructors; never replace their implementation.
// Offsets are explicitly confined to the frozen x86-64 library hash in PLAN.md.
#include <atomic>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <dlfcn.h>
#include <unistd.h>

struct Field {const char* name; unsigned offset; unsigned size; char type;};
static const Field fields[] = {
    {"getPlotPaperMarginLeftMM",0xd8,8,'d'}, {"getPlotPaperMarginBottomMM",0xe0,8,'d'},
    {"getPlotPaperMarginRightMM",0xe8,8,'d'}, {"getPlotPaperMarginTopMM",0xf0,8,'d'},
    {"getNumeratorCustomScale",0x178,8,'d'}, {"getDenominatorCustomScale",0x180,8,'d'},
    {"getPlotPaperUnits",0x188,4,'i'}, {"getPlotRotation",0x18c,4,'i'},
    {"getPlotType",0x190,4,'i'}, {"getUseStandardScale",0x194,1,'b'},
    {"getStandardScale",0x198,8,'d'}, {"getStandardScaleType",0x1a0,4,'i'},
    {"getTabOrder",0x30,4,'t'}
};
static std::atomic<unsigned long> sequence{0};
static void* real_symbol(const char* symbol) {
    void* fn=dlsym(RTLD_NEXT,symbol);
    if (!fn) {std::fprintf(stderr,"ICT_LAYOUT17_FATAL missing symbol %s\n",symbol);_exit(127);}
    return fn;
}
static const char* selected_mode() {
    const char* mode=std::getenv("ICT_LAYOUT17_MODE");
    if (!mode || (std::strcmp(mode,"observe") && std::strcmp(mode,"preset-a") &&
                  std::strcmp(mode,"preset-b") && std::strcmp(mode,"tab-only"))) {
        std::fprintf(stderr,"ICT_LAYOUT17_FATAL invalid mode\n");_exit(127);
    }
    return mode;
}
static void snapshot(void* object,unsigned char data[13][8]) {
    for (unsigned i=0;i<13;++i) std::memcpy(data[i],static_cast<unsigned char*>(object)+fields[i].offset,fields[i].size);
}
static void preset(void* object,const char* mode) {
    for (const auto& field:fields) {
        auto* dst=static_cast<unsigned char*>(object)+field.offset;
        if (!std::strcmp(mode,"tab-only") && field.type=='t') {int n=1234;std::memcpy(dst,&n,4);}
        if ((!std::strcmp(mode,"preset-a") || !std::strcmp(mode,"preset-b")) && field.type!='t') {
            bool b=!std::strcmp(mode,"preset-b");
            if (field.type=='d') {double n=b?2.25:1.125;std::memcpy(dst,&n,8);}
            else if (field.type=='i') {int n=b?1:0;std::memcpy(dst,&n,4);}
            else {unsigned char n=b?1:0;std::memcpy(dst,&n,1);}
        }
    }
}
static void hex(const unsigned char* data,unsigned size) {
    for (unsigned i=0;i<size;++i) std::fprintf(stderr,"%02x",data[i]);
}
static void report(unsigned long seq,const char* variant,const char* mode,
                   unsigned char original[13][8],unsigned char before[13][8],unsigned char after[13][8]) {
    flockfile(stderr);
    std::fprintf(stderr,"ICT_LAYOUT17_CTOR {\"sequence\":%lu,\"variant\":\"%s\",\"mode\":\"%s\",\"fields\":[",seq,variant,mode);
    for (unsigned i=0;i<13;++i) {
        const auto& f=fields[i];
        std::fprintf(stderr,"%s{\"getter\":\"%s\",\"offset\":%u,\"size\":%u,\"original\":\"",i?",":"",f.name,f.offset,f.size);
        hex(original[i],f.size);std::fprintf(stderr,"\",\"before_library\":\"");hex(before[i],f.size);
        std::fprintf(stderr,"\",\"after_library\":\"");hex(after[i],f.size);std::fprintf(stderr,"\"}");
    }
    std::fprintf(stderr,"]}\n");funlockfile(stderr);
}
static void defaults(void* object,const char* symbol) {
    using Ctor=void(*)(void*);static_assert(sizeof(int)==4 && sizeof(double)==8,"Frozen ABI only");
    auto fn=reinterpret_cast<Ctor>(real_symbol(symbol));const char* mode=selected_mode();
    unsigned char original[13][8]{},before[13][8]{},after[13][8]{};
    snapshot(object,original);preset(object,mode);snapshot(object,before);
    auto seq=++sequence;fn(object);snapshot(object,after);report(seq,symbol,mode,original,before,after);
}
static void named(void* object,void* document,const void* name,const char* symbol) {
    using Ctor=void(*)(void*,void*,const void*);
    auto fn=reinterpret_cast<Ctor>(real_symbol(symbol));const char* mode=selected_mode();
    unsigned char original[13][8]{},before[13][8]{},after[13][8]{};
    snapshot(object,original);preset(object,mode);snapshot(object,before);
    auto seq=++sequence;fn(object,document,name);snapshot(object,after);report(seq,symbol,mode,original,before,after);
}
extern "C" void default_c1(void*) asm("_ZN7RLayoutC1Ev");
extern "C" void default_c2(void*) asm("_ZN7RLayoutC2Ev");
extern "C" void named_c1(void*,void*,const void*) asm("_ZN7RLayoutC1EP9RDocumentRK7QString");
extern "C" void named_c2(void*,void*,const void*) asm("_ZN7RLayoutC2EP9RDocumentRK7QString");
extern "C" void default_c1(void* o) {defaults(o,"_ZN7RLayoutC1Ev");}
extern "C" void default_c2(void* o) {defaults(o,"_ZN7RLayoutC2Ev");}
extern "C" void named_c1(void* o,void* d,const void* n) {named(o,d,n,"_ZN7RLayoutC1EP9RDocumentRK7QString");}
extern "C" void named_c2(void* o,void* d,const void* n) {named(o,d,n,"_ZN7RLayoutC2EP9RDocumentRK7QString");}
