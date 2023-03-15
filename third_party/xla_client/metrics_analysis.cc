#include "third_party/xla_client/metrics_analysis.h"

#include "absl/strings/match.h"
#include "absl/strings/str_format.h"
#include "absl/types/variant.h"
#include "third_party/xla_client/metrics.h"
#include "third_party/xla_client/tf_logging.h"
#include "third_party/xla_client/types.h"

namespace xla {
namespace metrics {

namespace {

static const char* kAnalysisPrefix = "pt-xla-profiler";

float DivToFloat(std::ldiv_t val, std::int64_t denominator) {
  return val.quot + (float)val.rem / denominator;
}

class MetricFrequency : public Analyzer {
 public:
  MetricFrequency(std::string metric_name, float frequency_threshold,
                  long warmup_steps = 0)
      : metric_name_(metric_name),
        frequency_threshold_(frequency_threshold),
        warmup_steps_(warmup_steps) {}

  Analysis Run() override {
    CounterData* step = GetCounter("MarkStep");
    MetricData* metric = GetMetric(metric_name_);
    if (!step || !metric) {
      return {Analysis::Symptom::kNormal};
    }
    size_t metric_count = metric->TotalSamples();
    int64_t step_count = step->Value();
    if (step_count <= warmup_steps_) {
      return {Analysis::Symptom::kNormal};
    }
    auto res = std::div(metric_count, step_count);
    if (DivToFloat(res, step_count) > frequency_threshold_) {
      return {
          Analysis::Symptom::kMetricTooFrequent,
          absl::StrFormat("%s: %s too frequent: %zu counts during %zu steps",
                          kAnalysisPrefix, metric_name_, metric_count,
                          step_count),
      };
    }
    return {Analysis::Symptom::kNormal};
  }

 private:
  std::string metric_name_;
  float frequency_threshold_;
  long warmup_steps_;
};

class MetricTime : public Analyzer {
 public:
  MetricTime(std::string metric_name, long threshdold_nsec)
      : metric_name_(metric_name), threshold_nsec_(threshdold_nsec) {}

  Analysis Run() override {
    double max_metric_time = 0;
    MetricData* metric = GetMetric(metric_name_);
    if (!metric) {
      return {Analysis::Symptom::kNormal};
    }
    // No need for accumulator and we want all recent samples.
    for (const Sample& sample : metric->Samples(nullptr, nullptr)) {
      max_metric_time = std::max(sample.value, max_metric_time);
    }
    if (max_metric_time > threshold_nsec_) {
      return {
          Analysis::Symptom::kMetricTooSlow,
          absl::StrFormat("%s: %s too slow: longest instance took %s. "
                          "Please open a GitHub issue with the graph dump for "
                          "our team to optimize.",
                          kAnalysisPrefix, metric_name_,
                          xla::metrics::MetricFnTime(max_metric_time)),
      };
    }
    return {Analysis::Symptom::kNormal};
  }

 private:
  std::string metric_name_;
  long threshold_nsec_;
};

class UnloweredOp : public Analyzer {
 public:
  Analysis Run() override {
    std::stringstream ss;
    MetricsArena* arena = MetricsArena::Get();
    arena->ForEachCounter([&ss](const std::string& name, CounterData* data) {
      if (absl::StrContains(name, "aten::") &&
          name != "aten::_local_scalar_dense") {
        ss << name << ", ";
      }
    });

    std::string repr = ss.str();
    if (!repr.empty()) {
      return {Analysis::Symptom::kUnloweredOp,
              absl::StrCat(kAnalysisPrefix, ": Op(s) not lowered: ", repr,
                           " Please open a GitHub issue with the above op "
                           "lowering requests.")};
    }
    return {Analysis::Symptom::kNormal, repr};
  }
};

std::vector<Analyzer*>* GetAnalyzers() {
  static std::vector<Analyzer*>* analyzers = new std::vector<Analyzer*>{
      new MetricFrequency("CompileTime", 0.5f, 10),
      new MetricFrequency("TransferFromServerTime", 0.5f),
      new MetricTime("CompileTime", 300e9),
      new MetricTime("ExecuteTime", 30e9),
      new UnloweredOp(),
  };
  return analyzers;
}

}  // namespace

std::string CreatePerformanceReport(
    const std::map<std::string, xla::Metric>& rt_metrics) {
  std::stringstream ss;
  std::vector<Analyzer*>* analyzers = GetAnalyzers();
  for (auto const& analyzer : *analyzers) {
    Analysis result = analyzer->Run(rt_metrics);
    if (result.symptom != Analysis::Symptom::kNormal) {
      ss << result.repr << std::endl;
    }
  }
  return ss.str();
}

}  // namespace metrics
}  // namespace xla
