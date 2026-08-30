"""Generate evidence-based comparison outputs without retraining models."""
import os
from pathlib import Path
os.environ.setdefault("MPLCONFIGDIR",str(Path("outputs")/".matplotlib"))
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from api.services.prediction_comparison import align_prediction_files,calculate_metrics

OUT=Path("outputs")/"final_model_comparison"; FIG=OUT/"figures"
def main():
    OUT.mkdir(parents=True,exist_ok=True); FIG.mkdir(exist_ok=True)
    aligned,unavailable=align_prediction_files()
    if aligned.empty: raise RuntimeError("No compatible prediction CSVs")
    metrics=calculate_metrics(aligned); aligned.to_csv(OUT/"aligned_predictions.csv",index=False)
    metrics.to_csv(OUT/"metrics_and_ranking.csv",index=False)
    pd.DataFrame([{"model_id":k,"status":"unavailable","reason":v} for k,v in unavailable.items()]).to_csv(OUT/"unavailable_predictions.csv",index=False)
    sample=aligned.iloc[:96*7]; fig,ax=plt.subplots(figsize=(13,5)); ax.plot(sample.timestamp,sample.actual_kw,color="black",label="Actual",lw=1.5)
    for model_id in metrics.model_id: ax.plot(sample.timestamp,sample[model_id],label=model_id,alpha=.75,lw=.8)
    ax.set_ylabel("Load demand (kW)"); ax.legend(ncol=3); fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(FIG/"actual_vs_predicted.png",dpi=180); plt.close(fig)
    models=list(metrics.model_id); fig,axes=plt.subplots(1,len(models),figsize=(3.3*len(models),3.5),sharey=True)
    for ax,model_id in zip(np.atleast_1d(axes),models): ax.hist(aligned.actual_kw-aligned[model_id],bins=50); ax.set_title(model_id); ax.set_xlabel("Residual (kW)")
    fig.tight_layout(); fig.savefig(FIG/"residual_analysis.png",dpi=180); plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,5)); ax.boxplot([np.abs(aligned.actual_kw-aligned[m]) for m in models],tick_labels=models,showfliers=False); ax.tick_params(axis="x",rotation=25); ax.set_ylabel("Absolute error (kW)"); fig.tight_layout(); fig.savefig(FIG/"absolute_error_boxplot.png",dpi=180); plt.close(fig)
    threshold=aligned.actual_kw.quantile(.9); peaks=aligned[aligned.actual_kw>=threshold].iloc[:500]
    fig,ax=plt.subplots(figsize=(13,5)); ax.plot(peaks.timestamp,peaks.actual_kw,"k.",label="Actual")
    for model_id in models: ax.scatter(peaks.timestamp,peaks[model_id],s=4,label=model_id,alpha=.55)
    ax.legend(ncol=3); ax.set_ylabel("Peak load (kW)"); fig.tight_layout(); fig.savefig(FIG/"peak_demand_performance.png",dpi=180); plt.close(fig)
    # Paired moving-block bootstrap on absolute errors; no independence assumption across 15-minute rows.
    rng=np.random.default_rng(42); best=models[0]; rows=[]; block=96; reps=1000
    for other in models[1:]:
        diff=np.abs(aligned.actual_kw-aligned[best])-np.abs(aligned.actual_kw-aligned[other]); observed=float(diff.mean()); centered=diff-observed
        starts=np.arange(len(diff)-block+1); means=[]
        for _ in range(reps): means.append(np.concatenate([centered.iloc[s:s+block].to_numpy() for s in rng.choice(starts,int(np.ceil(len(diff)/block)))])[:len(diff)].mean())
        p=(np.count_nonzero(np.abs(means)>=abs(observed))+1)/(reps+1); rows.append({"model_a":best,"model_b":other,"mean_absolute_error_difference_kw":observed,"p_value":p})
    pd.DataFrame(rows).to_csv(OUT/"statistical_comparison.csv",index=False)
    pd.DataFrame([{"model_id":m,"MAE":float(metrics.loc[metrics.model_id==m,"MAE"].iloc[0]),"inference_ms":"unavailable","note":"No comparable measured batch-inference benchmark was supplied"} for m in models]).to_csv(OUT/"accuracy_vs_computational_cost.csv",index=False)
if __name__=="__main__": main()
