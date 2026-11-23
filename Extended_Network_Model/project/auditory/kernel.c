/* Fixed population sizes make the memory layout explicit. Rows receive, columns send. */
#include <math.h>
#include <stdint.h>
#include <string.h>

enum { NT=40, NS=40, NI=10, NL=40, NC=90 };
typedef struct {
    double dt, tau_rec, U, a_plus, a_minus, initial_resource, initial_voltage;
    int32_t thalamic_std, subplate_std, use_stdp;
} Parameters;

double membrane_step(double v, double ge, double gi, double dt, double tau_m) {
    double total = 1.0 + ge + gi;
    double equilibrium = (-65.0 - 80.0*gi) / total;
    return equilibrium + (v-equilibrium)*exp(-total*dt/tau_m);
}

/* input x is the available fraction before this recovery interval. */
static inline double recover_and_release(double *x, int n, double U,
                                         double recovery, int depression) {
    if (!depression) return n*U;
    double available = 1.0 - (1.0 - *x)*recovery;
    double remaining = available;
    for (int j=0; j<n; ++j) remaining *= 1.0-U;
    *x = remaining;
    return available-remaining;
}
double release_step(double *x, int n, double U, double dt, double tau, int depression) {
    return recover_and_release(x,n,U,exp(-dt/tau),depression);
}

double plastic_step(double w, double pre_trace, double post_trace, int npre, int npost,
                    double a_plus, double a_minus) {
    double delta = a_plus*(1.0-w)*pre_trace*npost - a_minus*w*post_trace*npre;
    return fmin(1.0, fmax(0.0, w+delta));
}

/* Sequential sweep over time. Synaptic fan-out is evaluated only on nonzero events. */
void simulate_network(const Parameters *p, int steps, const int32_t *inputs,
        const double *ts, const double *tl, const double *sl, const double *si,
        const double *il, const double *threshold, double *weights,
        uint8_t *spikes, int n_snapshots, const int32_t *snapshot_steps,
        double *history) {
    const double dt=p->dt, ex_decay=exp(-dt/5.0), in_decay=exp(-dt/10.0);
    const double ex_mid=sqrt(ex_decay), in_mid=sqrt(in_decay);
    const double recovery=exp(-dt/p->tau_rec), trace_decay=exp(-dt/20.0);
    const int delay=(int)lround(1.0/dt), ref=(int)lround(2.0/dt);
    double v[NC], ge[NC]={0}, gi[NC]={0}, x_thal[NT], x_sp[NS];
    double pre_trace[NT]={0}, post_trace[NL]={0};
    int next_active[NC]={0}, snapshot=0, group_counts[10]={0};
    for (int j=0; j<NC; ++j) v[j]=p->initial_voltage;
    for (int i=0; i<NT; ++i) x_thal[i]=p->initial_resource;
    for (int i=0; i<NS; ++i) x_sp[i]=p->initial_resource;
    /* Sentinels distinguish an absent contact from a present zero-weight
       contact even when a gain is zero. */
    for (int j=0; j<NL; ++j)
        for (int i=0; i<NT; ++i)
            if (weights[j*NT+i]>=0.0) group_counts[i/4]++;

    for (int k=0; k<=steps; ++k) {
        const uint8_t *now=spikes+(size_t)k*NC;
        const uint8_t *delivered=(k>=delay) ? spikes+(size_t)(k-delay)*NC : NULL;
        const int32_t *thal=inputs+(size_t)k*NT;
        /* Inputs timestamped at the final boundary can contribute to learning,
           but there is no following membrane interval. */
        int any_pre=0, any_post=0;
        for (int i=0; i<NT; ++i) {
            int n=thal[i];
            double q=recover_and_release(&x_thal[i],n,p->U,(k==0?1.0:recovery),p->thalamic_std);
            if (n==0) continue;
            any_pre=1;
            double gain=q/p->U;  /* gains specify fully recovered single-event conductance */
            for (int j=0; j<NS; ++j) ge[j] += ts[j*NT+i]*gain;
            for (int j=0; j<NL; ++j) {
                int ix=j*NT+i;
                if (weights[ix]>=0.) ge[NS+NI+j] += tl[ix]*weights[ix]*gain;
            }
        }
        for (int i=0; i<NS; ++i) {
            int n=delivered ? delivered[i] : 0;
            double q=recover_and_release(&x_sp[i],n,p->U,(k==0?1.0:recovery),p->subplate_std);
            if (!n) continue;
            for (int j=0; j<NL; ++j) ge[NS+NI+j] += sl[j*NS+i]*q/p->U;
            for (int j=0; j<NI; ++j) ge[NS+j] += si[j*NS+i]*q/p->U;
        }
        if (delivered) {
            for (int i=0; i<NI; ++i) if (delivered[NS+i])
                for (int j=0; j<NL; ++j) gi[NS+NI+j] += il[j*NI+i];
        }
        if (p->use_stdp) {
            for (int i=0; i<NT; ++i) pre_trace[i] *= trace_decay;
            for (int j=0; j<NL; ++j) {
                post_trace[j] *= trace_decay;
                if (now[NS+NI+j]) any_post=1;
            }
            if (any_pre || any_post) {
                for (int j=0; j<NL; ++j)
                    for (int i=0; i<NT; ++i) {
                        int ix=j*NT+i, post=now[NS+NI+j];
                        if (weights[ix]>=0.0 && (thal[i] || post))
                            weights[ix]=plastic_step(weights[ix],pre_trace[i],post_trace[j],
                                                      thal[i],post,p->a_plus,p->a_minus);
                    }
            }
            for (int i=0; i<NT; ++i) pre_trace[i] += thal[i];
            for (int j=0; j<NL; ++j) post_trace[j] += now[NS+NI+j];
        }
        if (snapshot<n_snapshots && k==snapshot_steps[snapshot]) {
            double *row=history+(size_t)snapshot*10;
            for (int j=0; j<NL; ++j)
                for (int i=0; i<NT; ++i)
                    if (weights[j*NT+i]>=0.) row[i/4]+=weights[j*NT+i];
            for (int g=0; g<10; ++g) row[g]=group_counts[g] ? row[g]/group_counts[g] : NAN;
            ++snapshot;
        }
        if (k==steps) break;
        for (int j=0; j<NC; ++j) {
            if (k>=next_active[j]) {
                double tau_m=(j>=NS && j<NS+NI) ? 12.0 : 20.0;
                v[j]=membrane_step(v[j],ge[j]*ex_mid,gi[j]*in_mid,dt,tau_m);
                if (v[j]>=threshold[j]) {
                    spikes[(size_t)(k+1)*NC+j]=1;
                    v[j]=-65.0;
                    next_active[j]=k+1+ref;
                }
            }
            ge[j]*=ex_decay;
            gi[j]*=in_decay;
        }
    }
}
