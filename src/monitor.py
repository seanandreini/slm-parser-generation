import pynvml, time, threading

class GPUMonitor:
  def __init__(self, device_index=0, interval=0.1):
    self.device_index = device_index
    self.interval = interval
    self.monitoring = False
    # self.energy_joules = 0.0
    self.peak_vram_mb = 0.0
    self._thread = None

  def _monitoring_loop(self):
    pynvml.nvmlInit()
    handle = pynvml.nvmlDeviceGetHandleByIndex(self.device_index)

    while self.monitoring:
      # power_w = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0
      # self.energy_joules += power_w * self.interval

      vram_used_mb = pynvml.nvmlDeviceGetMemoryInfo(handle).used / (1024*1024)
      if vram_used_mb > self.peak_vram_mb:
        self.peak_vram_mb = vram_used_mb

      time.sleep(self.interval)

    pynvml.nvmlShutdown()

  def start(self):
    # self.energy_joules = 0.0
    self.peak_vram_mb = 0.0
    self.monitoring = True
    self._thread = threading.Thread(target=self._monitoring_loop)
    self._thread.start()

  def stop(self):
    self.monitoring = False
    if self._thread:
      self._thread.join()
    return {
      #"energy_joules": self.energy_joules,
      "peak_vram_mb": round(self.peak_vram_mb, 1)
    }