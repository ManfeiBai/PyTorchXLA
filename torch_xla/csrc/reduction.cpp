#include "torch_xla/csrc/reduction.h"

#include "tensorflow/compiler/xla/literal_util.h"
#include "tensorflow/compiler/xla/xla_client/debug_macros.h"
#include "torch_xla/csrc/helpers.h"

namespace torch_xla {
namespace {

struct ReductionInfo {
  std::vector<xla::int64> new_dimensions;
  xla::int64 element_count = 1;
};

ReductionInfo GetReductionInfo(
    const xla::Shape& shape,
    tensorflow::gtl::ArraySlice<const xla::int64> dimensions,
    bool keep_reduced_dimensions) {
  ReductionInfo rinfo;
  size_t idim = 0;
  for (xla::int64 i = 0; i < shape.rank(); ++i) {
    if (idim < dimensions.size() && dimensions[idim] == i) {
      rinfo.element_count *= shape.dimensions(i);
      ++idim;
      if (keep_reduced_dimensions) {
        rinfo.new_dimensions.push_back(1);
      }
    } else if (keep_reduced_dimensions) {
      rinfo.new_dimensions.push_back(shape.dimensions(i));
    }
  }
  return rinfo;
}

xla::XlaComputation CreateAllComputation(xla::PrimitiveType type) {
  xla::XlaBuilder builder("AllComputation");
  xla::XlaOp x =
      xla::Parameter(&builder, 0, xla::ShapeUtil::MakeShape(type, {}), "x");
  xla::XlaOp y =
      xla::Parameter(&builder, 1, xla::ShapeUtil::MakeShape(type, {}), "y");
  xla::XlaOp zero =
      xla::ConstantLiteral(&builder, xla::LiteralUtil::Zero(type));
  xla::XlaOp one = xla::ConstantLiteral(&builder, xla::LiteralUtil::One(type));
  xla::Select(xla::And(xla::Ne(x, zero), xla::Ne(y, zero)), one, zero);
  return ConsumeValue(builder.Build());
}

xla::XlaComputation CreateAnyComputation(xla::PrimitiveType type) {
  xla::XlaBuilder builder("AnyComputation");
  xla::XlaOp x =
      xla::Parameter(&builder, 0, xla::ShapeUtil::MakeShape(type, {}), "x");
  xla::XlaOp y =
      xla::Parameter(&builder, 1, xla::ShapeUtil::MakeShape(type, {}), "y");
  xla::XlaOp zero =
      xla::ConstantLiteral(&builder, xla::LiteralUtil::Zero(type));
  xla::XlaOp one = xla::ConstantLiteral(&builder, xla::LiteralUtil::One(type));
  xla::Select(xla::Or(xla::Ne(x, zero), xla::Ne(y, zero)), one, zero);
  return ConsumeValue(builder.Build());
}

xla::XlaOp CreateSummation(
    const xla::XlaOp& input,
    tensorflow::gtl::ArraySlice<const xla::int64> dimensions,
    bool keep_reduced_dimensions, bool scale) {
  xla::Shape shape = XlaHelpers::ShapeOfXlaOp(input);
  xla::XlaOp init_value =
      XlaHelpers::ScalarValue<float>(0, shape.element_type(), input.builder());
  ReductionInfo rinfo =
      GetReductionInfo(shape, dimensions, keep_reduced_dimensions);
  xla::XlaOp result = xla::Reduce(
      input, init_value, XlaHelpers::CreateAddComputation(shape.element_type()),
      dimensions);
  if (scale && rinfo.element_count > 1) {
    xla::XlaOp scale = XlaHelpers::ScalarValue<float>(
        1.0f / static_cast<float>(rinfo.element_count), shape.element_type(),
        input.builder());
    result = xla::Mul(result, scale);
  }
  if (keep_reduced_dimensions) {
    result = xla::Reshape(result, rinfo.new_dimensions);
  }
  return result;
}

xla::XlaOp CreateProduct(
    const xla::XlaOp& input,
    tensorflow::gtl::ArraySlice<const xla::int64> dimensions,
    bool keep_reduced_dimensions) {
  xla::Shape shape = XlaHelpers::ShapeOfXlaOp(input);
  xla::XlaOp init_value =
      XlaHelpers::ScalarValue<float>(1, shape.element_type(), input.builder());
  ReductionInfo rinfo =
      GetReductionInfo(shape, dimensions, keep_reduced_dimensions);
  xla::XlaOp result = xla::Reduce(
      input, init_value, XlaHelpers::CreateMulComputation(shape.element_type()),
      dimensions);
  if (keep_reduced_dimensions) {
    result = xla::Reshape(result, rinfo.new_dimensions);
  }
  return result;
}

}  // namespace

xla::XlaOp BuildSum(const torch::jit::Node* node, const xla::XlaOp& operand) {
  if (node->get<bool>(at::attr::keepdim).value()) {
    XLA_ERROR() << "Sum with keepdim set not supported yet";
  }
  xla::Shape operand_shape = XlaHelpers::ShapeOfXlaOp(operand);
  xla::XlaOp init_value = XlaHelpers::ScalarValue<float>(
      0, operand_shape.element_type(), operand.builder());
  const auto dimensions_to_reduce =
      node->get<std::vector<int64_t>>(at::attr::dim).value();
  return xla::Reduce(
      operand, init_value,
      XlaHelpers::CreateAddComputation(operand_shape.element_type()),
      XlaHelpers::I64List(dimensions_to_reduce));
}

xla::XlaOp BuildProd(const torch::jit::Node* node, const xla::XlaOp& operand) {
  if (node->get<bool>(at::attr::keepdim).value()) {
    XLA_ERROR() << "Product with keepdim set not supported yet";
  }
  xla::Shape operand_shape = XlaHelpers::ShapeOfXlaOp(operand);
  xla::XlaOp init_value = XlaHelpers::ScalarValue<float>(
      1, operand_shape.element_type(), operand.builder());
  const auto dimensions_to_reduce =
      node->get<std::vector<int64_t>>(at::attr::dim).value();
  return xla::Reduce(
      operand, init_value,
      XlaHelpers::CreateMulComputation(operand_shape.element_type()),
      XlaHelpers::I64List(dimensions_to_reduce));
}

xla::XlaOp BuildMean(const xla::XlaOp& input,
                     tensorflow::gtl::ArraySlice<const xla::int64> dimensions,
                     bool keep_reduced_dimensions) {
  return CreateSummation(input, dimensions, keep_reduced_dimensions,
                         /*scale=*/true);
}

xla::XlaOp BuildSum(const xla::XlaOp& input,
                    tensorflow::gtl::ArraySlice<const xla::int64> dimensions,
                    bool keep_reduced_dimensions) {
  return CreateSummation(input, dimensions, keep_reduced_dimensions,
                         /*scale=*/false);
}

xla::XlaOp BuildProd(const xla::XlaOp& input,
                     tensorflow::gtl::ArraySlice<const xla::int64> dimensions,
                     bool keep_reduced_dimensions) {
  return CreateProduct(input, dimensions, keep_reduced_dimensions);
}

xla::XlaOp BuildAll(const xla::XlaOp& input,
                    tensorflow::gtl::ArraySlice<const xla::int64> dimensions,
                    bool keep_reduced_dimensions) {
  xla::Shape shape = XlaHelpers::ShapeOfXlaOp(input);
  ReductionInfo rinfo =
      GetReductionInfo(shape, dimensions, keep_reduced_dimensions);
  xla::XlaOp init_value = xla::ConstantLiteral(
      input.builder(), xla::LiteralUtil::One(shape.element_type()));
  xla::XlaOp result =
      xla::Reduce(input, init_value, CreateAllComputation(shape.element_type()),
                  dimensions);
  if (keep_reduced_dimensions) {
    result = xla::Reshape(result, rinfo.new_dimensions);
  }
  return result;
}

xla::XlaOp BuildAny(const xla::XlaOp& input,
                    tensorflow::gtl::ArraySlice<const xla::int64> dimensions,
                    bool keep_reduced_dimensions) {
  xla::Shape shape = XlaHelpers::ShapeOfXlaOp(input);
  ReductionInfo rinfo =
      GetReductionInfo(shape, dimensions, keep_reduced_dimensions);
  xla::XlaOp init_value = xla::ConstantLiteral(
      input.builder(), xla::LiteralUtil::Zero(shape.element_type()));
  xla::XlaOp result =
      xla::Reduce(input, init_value, CreateAnyComputation(shape.element_type()),
                  dimensions);
  if (keep_reduced_dimensions) {
    result = xla::Reshape(result, rinfo.new_dimensions);
  }
  return result;
}

}  // namespace torch_xla
