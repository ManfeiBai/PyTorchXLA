import os
import unittest
from typing import Callable, Dict, List

import torch
import torch_xla
# We need to import the underlying implementation function to register with the dispatcher
import torch_xla.experimental.fori_loop
from torch_xla.experimental.fori_loop import fori_loop
# from torch_xla.experimental.fori_loop import _xla_while_loop_warpper_bn
from torch._higher_order_ops.while_loop import while_loop
import torch_xla.core.xla_model as xm
import torch_xla.core.xla_builder as xb
import torch_xla.utils.utils as xu

import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

def _fake_while_loop_second(cond_fn, body_fn, operands):
  # operands need to be more than one here
  while cond_fn(*operands):
    operands = body_fn(*operands)
  return operands

def _fake_while_loop(cond_fn, body_fn, operands):
  # operands need to be more than one here
  while cond_fn(*operands):
    operands = body_fn(*operands)
  return operands


class WhileLoopTest(unittest.TestCase):

  def test_while_loop_tpu_subtraction_pure_torch(self):
    xm.mark_step()
    device = xm.xla_device()

    def cond_fn(iteri, x, y):
      return iteri > 0

    def body_fn(iteri, x, y):
      return iteri - 1, x, torch.sub(x, 1)

    init_val = torch.tensor(10)
    out_val = torch.tensor(15)
    iteri = torch.tensor(3)
    res = while_loop(cond_fn, body_fn, (iteri, init_val, out_val))
    expected = _fake_while_loop_second(cond_fn, body_fn, (iteri, init_val, out_val))
    self.assertEqual(res, expected)

  def test_while_loop_tpu_subtraction(self):
    xm.mark_step()
    device = xm.xla_device()

    def cond_fn(iteri, x):
      return iteri > 0

    def body_fn(iteri, x):
      return iteri - 1, torch.sub(x, 1)

    init_val = torch.tensor(10, dtype=torch.int32, device=device)
    iteri = torch.tensor(3, device=device)
    _, res = while_loop(cond_fn, body_fn, (iteri, init_val))
    _, expected = _fake_while_loop_second(cond_fn, body_fn, (iteri, init_val))
    print("res: ", res)
    print("expected: ", expected)
    # self.assertTrue(torch.all(torch.eq(res, expected)))

  def test_while_loop_tpu_addition_pure_torch(self):
    def cond_fn(iteri, x, y):
      return iteri > 0

    def body_fn(iteri, x, y):
      return iteri - 1, x, torch.add(x, 1)

    init_val = torch.tensor(3)
    out_val = torch.tensor(15)
    iteri = torch.tensor(10)
    res =  while_loop(cond_fn, body_fn, (iteri, init_val, out_val))
    expected = _fake_while_loop_second(cond_fn, body_fn, (iteri, init_val, out_val))
    self.assertEqual(res, expected)

  def test_while_loop_tpu_addition(self):
    xm.mark_step()
    device = xm.xla_device()

    def cond_fn(iteri, x):
      return iteri > 0

    def body_fn(iteri, x):
      return iteri - 1, torch.add(x, 1)

    init_val = torch.tensor(3, dtype=torch.int32, device=device)
    iteri = torch.tensor(10, device=device)
    _, res =  while_loop(cond_fn, body_fn, (iteri, init_val))
    print("res: ", res)
    _, expected = _fake_while_loop_second(cond_fn, body_fn, (iteri, init_val))
    print("expected: ", expected)
    # self.assertTrue(torch.all(torch.eq(res, expected)))
    # self.assertEqual(res, expected)

  def test_while_loop_tpu_addition_nested_pure_torch(self):

    def cond_fn(iteri, x, y):
      return iteri > 0

    def body_fn(iteri, x, y):
      return iteri - 1, x, torch.add(torch.add(x, 1), 1)

    init_val = torch.tensor(0)
    out_val = torch.tensor(0)
    iteri = torch.tensor(10)
    res =  while_loop(cond_fn, body_fn, (iteri, init_val, out_val))
    expected = _fake_while_loop_second(cond_fn, body_fn, (iteri, init_val, out_val))
    self.assertEqual(res, expected)

  def test_while_loop_tpu_addition_nested(self):
    xm.mark_step()
    device = xm.xla_device()

    def cond_fn(iteri, x):
      return iteri > 0

    def body_fn(iteri, x):
      return iteri - 1, torch.add(torch.add(x, 1), 1)

    init_val = torch.tensor(2, dtype=torch.int32, device=device)
    iteri = torch.tensor(10, device=device)
    _, res =  while_loop(cond_fn, body_fn, (iteri, init_val))
    _, expected = _fake_while_loop_second(cond_fn, body_fn, (iteri, init_val))
    self.assertTrue(torch.all(torch.eq(res, expected)))

  def test_while_loop_tpu_simple_linear_inside_loop_pure_torch(self):

    torch.set_grad_enabled(False)

    n_epochs = 3
    batch_size_train = 8
    batch_size_test = 10
    learning_rate = 0.01
    momentum = 0.5
    log_interval = 10
    random_seed = 1
    torch.backends.cudnn.enabled = False
    torch.manual_seed(random_seed)

    class SimpleLinear(torch.nn.Module):
      def __init__(self):
        super().__init__()
        self.linear = torch.nn.Linear(2, 2)

      def forward(self, iteri, x):

        def cond_fn(iteri, x):
          return iteri > 0

        def body_fn(iteri, x):
          return iteri - 1, self.linear(x)

        return while_loop(cond_fn, body_fn, (iteri, x))

      def forward_compare(self, iteri, x):
        y = self.linear(x)
        return iteri - 1, y

    linear_model = SimpleLinear()
    l_in_0 = torch.randn(2, 2, dtype=torch.float32)
    iteri = torch.tensor(2, dtype=torch.int32)
    _, res = linear_model(iteri, l_in_0)

    # === expected result after 2 iteration to be compared ===
    _, expected = linear_model.forward_compare(iteri, l_in_0)
    _, expected = linear_model.forward_compare(iteri, expected)

    self.assertTrue(torch.all(torch.eq(res, expected)))

  def test_while_loop_tpu_simple_linear_inside_loop(self):
    xm.mark_step()
    device = xm.xla_device()
    torch.set_grad_enabled(False)

    n_epochs = 3
    batch_size_train = 8
    batch_size_test = 10
    learning_rate = 0.01
    momentum = 0.5
    log_interval = 10
    random_seed = 1
    torch.backends.cudnn.enabled = False
    torch.manual_seed(random_seed)

    class SimpleLinear(torch.nn.Module):
      def __init__(self):
        super().__init__()
        self.linear = torch.nn.Linear(2, 2)

      def forward(self, iteri, x):

        def cond_fn(iteri, x):
          return iteri > 0

        def body_fn(iteri, x):
          return iteri - 1, self.linear(x)

        return while_loop(cond_fn, body_fn, (iteri, x))

      def forward_compare(self, iteri, x):
        y = self.linear(x)
        return iteri - 1, y

    linear_model = SimpleLinear()
    linear_model.to(device)
    l_in_0 = torch.randn(2, 2, dtype=torch.float32, device=device)
    iteri = torch.tensor(2, dtype=torch.int32, device=device)
    _, res = linear_model(iteri, l_in_0)

    # === expected result after 2 iteration to be compared ===
    _, expected = linear_model.forward_compare(iteri, l_in_0)
    _, expected = linear_model.forward_compare(iteri, expected)

    self.assertTrue(torch.all(torch.eq(res, expected)))

  def test_while_loop_tpu_MNIST_inside_loop_pure_torch(self):

    torch.set_grad_enabled(False)

    n_epochs = 3
    batch_size_train = 8
    batch_size_test = 10
    learning_rate = 0.01
    momentum = 0.5
    log_interval = 10
    random_seed = 1
    torch.backends.cudnn.enabled = False
    torch.manual_seed(random_seed)

    class MNIST(torch.nn.Module):
      def __init__(self):
        super().__init__()
        self.conv1 = torch.nn.Conv2d(1, 10, kernel_size=5, stride=1, padding=2)
        self.bn1 = torch.nn.BatchNorm2d(10)
        self.conv2 = torch.nn.Conv2d(10, 20, kernel_size=5)
        self.bn2 = torch.nn.BatchNorm2d(20)
        self.fc1 = torch.nn.Linear(500, 50)
        self.fc2 = torch.nn.Linear(50, 10)

      def forward(self, iteri, x, y):
        def cond_fn(iteri, x, y):
          return iteri > 0

        def body_fn(iteri, x, y):
          y = F.relu(F.max_pool2d(self.conv1(x), 2))
          y = self.bn1(y) # torch.while_loop's body_fn might be modifying the input!
          y = F.relu(F.max_pool2d(self.conv2(y), 2))
          y = self.bn2(y)
          y = torch.flatten(y, 1)
          y = F.relu(self.fc1(y))
          y = self.fc2(y)

          return iteri - 1, x.clone(), F.log_softmax(y, dim=1)

        return while_loop(cond_fn, body_fn, (iteri, x, y))

      def forward_compare(self, iteri, x, y):
        y = F.relu(F.max_pool2d(self.conv1(x), 2))
        y = self.bn1(y) # torch.while_loop's body_fn might be modifying the input!
        y = F.relu(F.max_pool2d(self.conv2(y), 2))
        y = self.bn2(y)
        y = torch.flatten(y, 1)
        y = F.relu(self.fc1(y))
        y = self.fc2(y)
        return iteri - 1, x.clone(), F.log_softmax(y, dim=1)

    mnist = MNIST()
    bs=16
    l_in_0 = torch.randn(bs, 1, 28, 28, dtype=torch.float32)
    l_out = torch.randn(bs, 10, dtype=torch.float32)
    iteri = torch.tensor(3, dtype=torch.int64)
    _, _, res = mnist(iteri, l_in_0, l_out)

    # === expected result for one iteration to be compared since body_fn defined use the same input in each iteration ===
    _, _, expected_res = mnist.forward_compare(iteri, l_in_0, l_out)
    self.assertTrue(torch.all(torch.eq(res, expected_res)))

  def test_while_loop_tpu_MNIST_inside_loop_without_BN(self):
    xm.mark_step()
    device = xm.xla_device()
    torch.set_grad_enabled(False)

    n_epochs = 3
    batch_size_train = 8
    batch_size_test = 10
    learning_rate = 0.01
    momentum = 0.5
    log_interval = 10
    random_seed = 1
    torch.backends.cudnn.enabled = False
    torch.manual_seed(random_seed)

    class MNIST(torch.nn.Module):
      def __init__(self):
        super().__init__()
        self.conv1 = torch.nn.Conv2d(1, 10, kernel_size=5, stride=1, padding=2)
        self.bn1 = torch.nn.BatchNorm2d(10)
        self.conv2 = torch.nn.Conv2d(10, 20, kernel_size=5)
        self.bn2 = torch.nn.BatchNorm2d(20)
        self.fc1 = torch.nn.Linear(500, 50)
        self.fc2 = torch.nn.Linear(50, 10)

      def forward(self, iteri, x, y):
        def cond_fn(iteri, x, y):
          return iteri > 0

        def body_fn(iteri, x, y):
          y = F.relu(F.max_pool2d(self.conv1(x), 2))
          # y = self.bn1(y)
          y = F.relu(F.max_pool2d(self.conv2(y), 2))
          # y = self.bn2(y)
          y = torch.flatten(y, 1)
          y = F.relu(self.fc1(y))
          y = self.fc2(y)

          return iteri - 1, x.clone(), F.log_softmax(y, dim=1)

        return while_loop(cond_fn, body_fn, (iteri, x, y))

      def forward_compare(self, iteri, x, y):
        y = F.relu(F.max_pool2d(self.conv1(x), 2))
        # y = self.bn1(y)
        y = F.relu(F.max_pool2d(self.conv2(y), 2))
        # y = self.bn2(y)
        y = torch.flatten(y, 1)
        y = F.relu(self.fc1(y))
        y = self.fc2(y)
        return iteri - 1, x.clone(), F.log_softmax(y, dim=1)


    mnist = MNIST()
    mnist.to(device)
    bs=16
    l_in_0 = torch.randn(bs, 1, 28, 28, dtype=torch.float32, device=device)
    l_out = torch.randn(bs, 10, dtype=torch.float32, device=device)
    iteri = torch.tensor(3, dtype=torch.int64, device=device)
    _, _, res = mnist(iteri, l_in_0, l_out)
    # print("res: ", res)
    print("res[0]: ", res[0])

    # === expected result for one iteration to be compared since body_fn defined use the same input in each iteration ===
    _, _, expected_res = mnist.forward_compare(iteri, l_in_0, l_out)
    # print("expected_res: ", expected_res)
    print("expected_res[0]: ", expected_res[0])
    self.assertTrue(torch.all(torch.eq(res, expected_res)))

  def test_while_loop_tpu_MNIST_inside_loop(self):
    xm.mark_step()
    device = xm.xla_device()
    torch.set_grad_enabled(False)

    n_epochs = 3
    batch_size_train = 8
    batch_size_test = 10
    learning_rate = 0.01
    momentum = 0.5
    log_interval = 10
    random_seed = 1
    torch.backends.cudnn.enabled = False
    torch.manual_seed(random_seed)

    class MNIST(torch.nn.Module):
      def __init__(self):
        super().__init__()
        self.conv1 = torch.nn.Conv2d(1, 10, kernel_size=5, stride=1, padding=2)
        self.bn1 = torch.nn.BatchNorm2d(10, affine=False, track_running_stats=False)
        self.conv2 = torch.nn.Conv2d(10, 20, kernel_size=5)
        self.bn2 = torch.nn.BatchNorm2d(20, affine=False, track_running_stats=False)
        self.fc1 = torch.nn.Linear(500, 50)
        self.fc2 = torch.nn.Linear(50, 10)
        self.bnLayersWeights = []

      def forward(self, iteri, x, y):
        def cond_fn(iteri, x, y):
          return iteri > 0

        def body_fn(iteri, x, y):
          y = F.relu(F.max_pool2d(self.conv1(x), 2))
          y = self.bn1(y)
          y = F.relu(F.max_pool2d(self.conv2(y), 2))
          y = self.bn2(y)
          y = torch.flatten(y, 1)
          y = F.relu(self.fc1(y))
          y = self.fc2(y)

          return iteri - 1, x.clone(), F.log_softmax(y, dim=1)

        return while_loop(cond_fn, body_fn, (iteri, x, y))

      def forward_compare(self, iteri, x, y):
        y = F.relu(F.max_pool2d(self.conv1(x), 2))
        y = self.bn1(y)
        y = F.relu(F.max_pool2d(self.conv2(y), 2))
        y = self.bn2(y)
        y = torch.flatten(y, 1)
        y = F.relu(self.fc1(y))
        y = self.fc2(y)
        return iteri - 1, x.clone(), F.log_softmax(y, dim=1)

    mnist = MNIST()
    mnist.to(device)
    bs=16
    l_in_0 = torch.randn(bs, 1, 28, 28, dtype=torch.float32, device=device)
    l_out = torch.randn(bs, 10, dtype=torch.float32, device=device)
    iteri = torch.tensor(3, dtype=torch.int64, device=device)
    _, _, res = mnist(iteri, l_in_0, l_out)
    # _, _, res = mnist(iteri, l_in_0)
    # print("res: ", res)
    print("res[0]: ", res[0])

    # === expected result for one iteration to be compared since body_fn defined use the same input in each iteration ===
    _, _, expected_res = mnist.forward_compare(iteri, l_in_0, l_out)
    # _, _, expected_res = mnist.forward_compare(iteri, l_in_0)
    # print("expected_res: ", expected_res)
    print("expected_res[0]: ", expected_res[0])
    self.assertTrue(torch.all(torch.eq(res, expected_res)))

  def test_while_loop_tpu_MNIST_inside_loop_with_mutation_in_batchnorm2d(self):
    xm.mark_step()
    device = xm.xla_device()
    torch.set_grad_enabled(False)

    n_epochs = 3
    batch_size_train = 8
    batch_size_test = 10
    learning_rate = 0.01
    momentum = 0.5
    log_interval = 10
    random_seed = 1
    torch.backends.cudnn.enabled = False
    torch.manual_seed(random_seed)

    class MNIST(torch.nn.Module):
      def __init__(self):
        super().__init__()
        self.conv1 = torch.nn.Conv2d(1, 10, kernel_size=5, stride=1, padding=2)
        # self.bn1 = torch.nn.BatchNorm2d(10, affine=False, track_running_stats=False)
        self.bn1 = torch.nn.BatchNorm2d(10).eval()
        # self.bn1 = torch.nn.BatchNorm2d(10)
        self.conv2 = torch.nn.Conv2d(10, 20, kernel_size=5)
        # self.bn2 = torch.nn.BatchNorm2d(20, affine=False, track_running_stats=False)
        self.bn2 = torch.nn.BatchNorm2d(20).eval()
        # self.bn2 = torch.nn.BatchNorm2d(20)
        self.fc1 = torch.nn.Linear(500, 50)
        self.fc2 = torch.nn.Linear(50, 10)
        self.bnLayersWeights = []

      def forward(self, iteri, x, y):
        def cond_fn(iteri, x, y):
          return iteri > 0

        def body_fn(iteri, x, y):
          y = F.relu(F.max_pool2d(self.conv1(x), 2))
          y = self.bn1(y)
          y = F.relu(F.max_pool2d(self.conv2(y), 2))
          y = self.bn2(y)
          y = torch.flatten(y, 1)
          y = F.relu(self.fc1(y))
          y = self.fc2(y)

          return iteri - 1, x.clone(), F.log_softmax(y, dim=1)

        return while_loop(cond_fn, body_fn, (iteri, x, y))

      def forward_compare(self, iteri, x, y):
        y = F.relu(F.max_pool2d(self.conv1(x), 2))
        y = self.bn1(y)
        y = F.relu(F.max_pool2d(self.conv2(y), 2))
        y = self.bn2(y)
        y = torch.flatten(y, 1)
        y = F.relu(self.fc1(y))
        y = self.fc2(y)
        return iteri - 1, x.clone(), F.log_softmax(y, dim=1)

    mnist = MNIST()
    mnist.to(device)
    bs=16
    l_in_0 = torch.randn(bs, 1, 28, 28, dtype=torch.float32, device=device)
    l_out = torch.randn(bs, 10, dtype=torch.float32, device=device)
    iteri = torch.tensor(3, dtype=torch.int64, device=device)

    # print("print and check behavior by exporting the model")
    # ep = torch.export.export(mnist, (iteri, l_in_0, l_out))
    # ep.module().print_readable()
    # print("after print and check behavior by exporting the model")

    _, _, res = mnist(iteri, l_in_0, l_out)
    # _, _, res = mnist(iteri, l_in_0)
    # print("res: ", res)
    print("res[0]: ", res[0])

    # === expected result for one iteration to be compared since body_fn defined use the same input in each iteration ===
    _, _, expected_res = mnist.forward_compare(iteri, l_in_0, l_out)
    # _, _, expected_res = mnist.forward_compare(iteri, l_in_0)
    # print("expected_res: ", expected_res)
    print("expected_res[0]: ", expected_res[0])
    self.assertTrue(torch.all(torch.eq(res, expected_res)))

  def test_while_loop_tpu_MNIST_inside_loop_pure_torch_xla_without_while_loop(self):
    xm.mark_step()
    device = xm.xla_device()
    torch.set_grad_enabled(False)

    n_epochs = 3
    batch_size_train = 8
    batch_size_test = 10
    learning_rate = 0.01
    momentum = 0.5
    log_interval = 10
    random_seed = 1
    torch.backends.cudnn.enabled = False
    torch.manual_seed(random_seed)

    class MNIST(torch.nn.Module):
      def __init__(self):
        super().__init__()
        self.conv1 = torch.nn.Conv2d(1, 10, kernel_size=5, stride=1, padding=2)
        self.bn1 = torch.nn.BatchNorm2d(10)
        self.conv2 = torch.nn.Conv2d(10, 20, kernel_size=5)
        self.bn2 = torch.nn.BatchNorm2d(20)
        self.fc1 = torch.nn.Linear(500, 50)
        self.fc2 = torch.nn.Linear(50, 10)
        self.bnLayersWeights = []

      def forward(self, x, y):
        y = F.relu(F.max_pool2d(self.conv1(x), 2))
        y = self.bn1(y) # torch.while_loop's body_fn might be modifying the input!
        y = F.relu(F.max_pool2d(self.conv2(y), 2))
        y = self.bn2(y)
        y = torch.flatten(y, 1)
        y = F.relu(self.fc1(y))
        y = self.fc2(y)
        return x.clone(), F.log_softmax(y, dim=1)

    mnist = MNIST()
    mnist.to(device)
    bs=16
    l_in_0 = torch.randn(bs, 1, 28, 28, dtype=torch.float32, device=device)
    l_out = torch.randn(bs, 10, dtype=torch.float32, device=device)
    iteri = torch.tensor(3, dtype=torch.int64, device=device)
    _, res = mnist(l_in_0, l_out)
    # print("res: ", res)
    print("res[0]: ", res[0])

  # ====== test _get_xla_computation ======
  def test__get_xlacomputation(self):

    xm.mark_step()
    device = xm.xla_device()
    t1 = torch.randn(20, 5).to(device)
    t2 = torch.randn(20, 5).to(device)
    t3 = torch.add(t1, t2)

    ### implement one new function for xlacomputation generation with post-order
    res_xla_computation = torch_xla._XLAC._get_xla_computation([t3], [], True, "", [])
    if res_xla_computation:
      hlo_print = xb.get_computation_hlo(res_xla_computation)
      print("Gain and print computation from _get_xla_computation") # print(hlo_print)
    else:
      print("Failed to gain or print computation(null) from _get_xla_computation")

  def test_PyLoweringContext_and__get_xlacomputation_with_simple_linear_tpu(self):

    xm.mark_step()
    device = xm.xla_device()
    torch.set_grad_enabled(False)

    class SimpleWithLinear(torch.nn.Module):
      def __init__(self):
        super().__init__()
        self.linear = torch.nn.Linear(2, 2)
        self.register_buffer("dec", torch.tensor(1))

      def forward(self, x):
        x = self.linear(x)
        return x

    simple_with_linear = SimpleWithLinear()
    simple_with_linear.to(device)
    input = torch.randn(2, 2).to(device)
    t3 = simple_with_linear(input)

    def cond_fn(upper, lower, one_value, x, input_value, output_value, *args):
      return lower[0] < upper[0]

    def body_fn(upper, lower, one_value, x, input_value, output_value, *args):
      new_lower = torch.add(one_value, lower)
      output_value = simple_with_linear(input_value)
      res = [upper.clone(), new_lower.clone(), one_value.clone(), torch.add(one_value, x), input_value.clone(), output_value.clone()]
      return tuple(res)

    ### implement one new function for xlacomputation generation with post-order
    res_xla_computation = torch_xla._XLAC._get_xla_computation([t3], [], True, "", [])
    if res_xla_computation:
      hlo_print = xb.get_computation_hlo(res_xla_computation)
      print("Gain and print computation from _get_xla_computation") # print(hlo_print)
    else:
      print("Failed to gain or print computation(null) from _get_xla_computation")

    ### get xlacomputation via PyLoweringContext
    body_ctx = torch_xla._XLAC.lowering.LoweringContext()
    body_ctx.set_name_string("bodyctx")
    body_ctx.buildforiloop(list(t3), [])
    body_hlo = body_ctx.hlo()
    body_computation = xb.computation_from_module_proto("bodycomputation",
                                                        body_hlo)
    body_hlo_print = xb.get_computation_hlo(body_computation)
    print("Gain and print computation from PyLoweringContext") # print(body_hlo_print)

  # ====== fori_loop ======
  def test_fori_loop_addition_tpu(self):
    xm.mark_step()
    device = xm.xla_device()

    lower = torch.tensor(0, device=device)
    upper = torch.tensor(50, device=device)
    init_val = torch.tensor(1, dtype=torch.int32, device=device)

    def body_fun(x):
      return torch.add(x, 1)

    _, actual = fori_loop(upper, lower, body_fun, (init_val))
    print("actual: ", actual)

    # === expected ===
    x = init_val
    for i in range(upper - lower):
      x = torch.add(x, 1)
    expected = x
    print("expected: ", expected)


if __name__ == '__main__':
  test = unittest.main()
  sys.exit(0 if test.result.wasSuccessful() else 1)
