#pragma once

#include "absl/types/span.h"
#include "xla/xla_data.pb.h"
#include "torch_xla/csrc/ir.h"

namespace torch_xla {

class ConvolutionBackwardOverrideable : public XlaNode {
 public:
  ConvolutionBackwardOverrideable(
      const torch::lazy::Value& grad_output, const torch::lazy::Value& input,
      const torch::lazy::Value& weight, std::vector<int64_t> stride,
      std::vector<int64_t> padding, std::vector<int64_t> dilation,
      bool transposed, std::vector<int64_t> output_padding, int64_t groups);

  torch::lazy::NodePtr Clone(torch::lazy::OpList operands) const override;

  XlaOpVector Lower(LoweringContext* loctx) const override;

  std::string ToString() const override;

  const std::vector<int64_t>& stride() const { return stride_; }

  const std::vector<int64_t>& padding() const { return padding_; }

  const std::vector<int64_t>& dilation() const { return dilation_; }

  bool transposed() const { return transposed_; }

  const std::vector<int64_t>& output_padding() const { return output_padding_; }

  int64_t groups() const { return groups_; }

 private:
  std::vector<int64_t> stride_;
  std::vector<int64_t> padding_;
  std::vector<int64_t> dilation_;
  std::vector<int64_t> output_padding_;
  bool transposed_;
  int64_t groups_;
};

}  // namespace torch_xla
