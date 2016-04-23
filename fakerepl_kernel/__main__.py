from ipykernel.kernelapp import IPKernelApp
from .kernel import FakeReplKernel
IPKernelApp.launch_instance(kernel_class=FakeReplKernel)
