resource_groups = [
  {
    name   = "AI-cluster-east"
    region = "eastus"
    aks_clusters = [
      {
        name = "aks-gpu-cluster-1"
        zone = "eastus-1"
        node_pools = [
          {
            name                   = "gpu-premium-pool"
            gpu_type               = "H100"
            memory_gb              = 640
            network_bandwidth_gbps = 800
            cost_per_hour          = 32.5
            node_count             = 8
          },
          {
            name                   = "gpu-standard-pool"
            gpu_type               = "L4"
            memory_gb              = 192
            network_bandwidth_gbps = 200
            cost_per_hour          = 6.5
            node_count             = 12
          }
        ]
      }
    ]
  },
  {
    name   = "AI-cluster-west"
    region = "westus"
    aks_clusters = [
      {
        name = "aks-gpu-cluster-2"
        zone = "westus-2"
        node_pools = [
          {
            name                   = "gpu-premium-pool"
            gpu_type               = "A100"
            memory_gb              = 640
            network_bandwidth_gbps = 400
            cost_per_hour          = 24
            node_count             = 6
          }
        ]
      }
    ]
  }
]

