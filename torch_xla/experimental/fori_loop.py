import numpy as np
import torch
import torch_xla
import torch_xla.core.xla_builder as xb
import torch_xla.core.xla_model as xm
import torch_xla.utils.utils as xu
import torch_xla.core.xla_op_registry as xor

from torch._C import DispatchKey
from torch._ops import HigherOrderOperator
import torch._higher_order_ops.while_loop
from torch._higher_order_ops.while_loop import while_loop_op


### TODO(@manfei): treat *input_value
def fori_loop(upper, lower, body_fun, init_val, input_value):

  device = xm.xla_device()
  # body_fun = torch.nn.Linear(10, 20).to(xm.xla_device())

  output_value = torch.zeros([20], dtype=torch.float32, device=device)
  one_value = torch.tensor([1], dtype=torch.int32, device=device)

  def cond_fn(upper, lower, one_value, x, input_value, output_value):
    return lower[0] < upper[0]
  def body_fn(upper, lower, one_value, x, input_value, output_value):
    new_lower = torch.add(one_value, lower)
    output_value = body_fun(input_value)
    weight = body_fun.weight  ### not be used actually, initialized as placeholder xlacomputation requirement
    bias = body_fun.bias  ### not be used actually, initialized as placeholder xlacomputation requirement
    # return upper, new_lower, one_value, torch.add(one_value, x), input_value, weight, bias, output_value
    return upper.clone(), new_lower.clone(), one_value.clone(), torch.add(one_value, x), input_value.clone(), bias.clone(), weight.clone(), output_value.clone() 
  # weight_0 = body_fun.weight
  # bias_0 = body_fun.bias
  res = while_loop(cond_fn, body_fn, (upper, lower, one_value, init_val, input_value, output_value))
  return res

  if (hasattr(body_fun, 'weight') or hasattr(body_fun, 'bias')):
    # print("body_fun.weight: ", body_fun.weight)
    # print("body_fun.bias: ", body_fun.bias)
    def cond_fn(upper, lower, one_value, x, input_value, output_value):
      return lower[0] < upper[0]
    def body_fn(upper, lower, one_value, x, input_value, output_value):
      new_lower = torch.add(one_value, lower)
      output_value = body_fun(input_value)
      weight = body_fun.weight  ### not be used actually, initialized as placeholder xlacomputation requirement
      bias = body_fun.bias  ### not be used actually, initialized as placeholder xlacomputation requirement
      # return upper, new_lower, one_value, torch.add(one_value, x), input_value, weight, bias, output_value
      return upper.clone(), new_lower.clone(), one_value.clone(), torch.add(one_value, x), input_value.clone(), bias.clone(), weight.clone(), output_value.clone() 
    # weight_0 = body_fun.weight
    # bias_0 = body_fun.bias
    res = while_loop(cond_fn, body_fn, (upper, lower, one_value, init_val, input_value, output_value))
  else:
    def cond_fn(upper, lower, one_value, x, input_value, output_value):
      return lower[0] < upper[0]
    def body_fn(upper, lower, one_value, x, input_value, output_value):
      new_lower = torch.add(one_value, lower)
      output_value = body_fun(input_value)
      return upper, new_lower, one_value, torch.add(one_value, x), input_value, output_value
    res = while_loop(cond_fn, body_fn, (upper, lower, one_value, init_val, input_value, output_value))

  # output_value = torch.zeros([20], dtype=torch.float32, device=device)
  # one_value = torch.tensor([1], dtype=torch.int32, device=device)
  # if (hasattr(body_fun, 'weight') or hasattr(body_fun, 'bias')):
  #   weight_0 = body_fun.weight
  #   bias_0 = body_fun.bias
  #   res = while_loop(cond_fn, body_fn, (upper, lower, one_value, init_val, *input_value, weight_0, bias_0, output_value))
  # else:
  #   res = while_loop(cond_fn, body_fn, (upper, lower, one_value, init_val, *input_value, output_value))
  return res


@while_loop_op.py_impl(DispatchKey.XLA)
def while_loop(cond_fn, body_fn, carried_inputs, additional_inputs=None):
  ### TODO(@manfei): PyTorch require carried_inputs to be list/tuple, PyTorch/XLA _xla_while_loop only accept *operands, *operands would tuple items again: (a, '')
  ### cond_fn&body_fn: callable
  ### carried_inputs: (Tuple of possibly nested dict/list/tuple of tensors)
  print("arrive here @while_loop_op.py_impl(DispatchKey.XLA) !!!")
  print("carried_inputs: ", carried_inputs)
  print("additional_inputs: ", additional_inputs)
  if additional_inputs is None:
    additional_inputs = tuple()
  return _xla_while_loop(cond_fn, body_fn, carried_inputs, additional_inputs)


def _xla_while_loop(cond_fn, body_fn, carried_inputs, additional_inputs=None):
  print("arrive here _xla_while_loop(cond_fn, body_fn, carried_inputs, additional_inputs=None): !!!")
  ### fake carried_inputs to split formal code
  fake_carried_inputs = []
  for carried_input in carried_inputs:
    device = carried_input.device
    ###TODO(@manfei) type = carried_input.type
    fake_carried_inputs.append(
        torch.randint(10, carried_input.size(),
                      dtype=carried_input.dtype).to(device))
  for additional_input in additional_inputs:
    device = additional_input.device
    ###TODO(@manfei) type = carried_input.type
    fake_carried_inputs.append(
        torch.randint(10, additional_input.size(),
                      dtype=additional_input.dtype).to(device))
  print("fake_carried_inputs: ", fake_carried_inputs)

  ### TODO(@manfei): specify which element is for which argument like a,b,c
  cond_result = cond_fn(*fake_carried_inputs)
  cond_ctx = torch_xla._XLAC.lowering.LoweringContext()
  cond_ctx.set_name_string("condctx")

  # # !!! cond xlacomputation change !!! switch bias and weight position
  # additional_inputs_list_cond = list(fake_carried_inputs[2:]) ### all missed arguments except upper/lower due to PyTorch/XLA trace from output tensor
  # tmp_bias = additional_inputs_list_cond[-2] ### not used, change order doesn't affect logic
  # del additional_inputs_list_cond[-2] ### not used, change order doesn't affect logic
  # additional_inputs_list_cond.append(tmp_bias) ### not used, change order doesn't affect logic

  # !!! cond xlacomputation change !!! switch output_value and weight position
  additional_inputs_list_cond = list(fake_carried_inputs[2:]) ### all missed arguments except upper/lower due to PyTorch/XLA trace from output tensor
  tmp_bias = additional_inputs_list_cond[-3] ### not used, change order doesn't affect logic
  del additional_inputs_list_cond[-3] ### not used, change order doesn't affect logic
  additional_inputs_list_cond.append(tmp_bias) ### not used, change order doesn't affect logic

  cond_ctx.buildforiloop([cond_result], additional_inputs_list_cond)
  cond_hlo = cond_ctx.hlo()
  cond_computation = xb.computation_from_module_proto("condcomputation",
                                                      cond_hlo)
  # cond_hlo_print = xb.get_computation_hlo(cond_computation)
  # print("cond computation: !!!!!!!!!")
  # print(cond_hlo_print)

  ### generate body_fn xlacomputation
  body_result = body_fn(*fake_carried_inputs)
  body_ctx = torch_xla._XLAC.lowering.LoweringContext()
  body_ctx.set_name_string("bodyctx")

  # !!! body xlacomputation change !!! add non-changed output_value argument
  additional_inputs_list_body = [fake_carried_inputs[-3]]

  ### TODO(@manfei): treat hard-code parameters: additional_inputs_list_body
  body_ctx.buildforiloop(list(body_result), additional_inputs_list_body)
  body_hlo = body_ctx.hlo()
  body_computation = xb.computation_from_module_proto("bodycomputation",
                                                      body_hlo)
  # body_hlo_print = xb.get_computation_hlo(body_computation)
  # print("body computation: !!!!!!!!!")
  # print(body_hlo_print)

  ### trans fake_carried_inputs from list(tensor) to list(xla::op), which part could change init of xla::while
  total_inputs = carried_inputs + additional_inputs
  kwargs = {}
  if type(total_inputs) is tuple:
    shapes = xb.tensor_shape(total_inputs)
  else:
    shapes = xb.tensor_shape((total_inputs))
  builder = xb.create_builder('test_while')
  params = []
  for shape in shapes:
    p = xb.mkparam(builder, len(params), shape)
    params.append(p)

  # ### TODO(@manfei): treat hard-code input arguments
  # # !!! init change !!! 
  # tmp_bias = params[-2]
  # del params[-2]
  # params.append(tmp_bias)

  ### TODO(@manfei): treat hard-code input arguments
  # !!! init change !!! switch bias and output_value
  tmp_bias = params[-3]
  del params[-3]
  params.append(tmp_bias)

  ### generate while xlacomputation
  input_tuple = xb.Op.tuple(tuple(params))
  w = xb.mkop(
      'While', (input_tuple.op,),
      condition_computation=cond_computation,
      body_computation=body_computation)
  name = 'fori_loop_ed_torch_func'
  computation = w.build(name)
  # hlo_print = xb.get_computation_hlo(computation)
  # print("while computation: !!!!!!!!!")
  # print(hlo_print)

  ### gain final result with generated while xlacomputation
  result = torch_xla._XLAC._xla_user_computation('xla::_op_test_while',
                                                 (total_inputs),
                                                 computation)
  ### print("!!! arrive here too after while!!!")

  return result