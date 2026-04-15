terraform {
  required_version = ">= 1.6.0"
}

variable "resource_groups" {
  type = list(object({
    name   = string
    region = string
    aks_clusters = list(object({
      name = string
      zone = string
      node_pools = list(object({
        name                    = string
        gpu_type                = string
        memory_gb               = number
        network_bandwidth_gbps  = number
        cost_per_hour           = number
        node_count              = number
      }))
    }))
  }))
}

locals {
  flat_node_pools = flatten([
    for rg in var.resource_groups : [
      for cluster in rg.aks_clusters : [
        for pool in cluster.node_pools : {
          resource_group = rg.name
          region         = rg.region
          cluster_name   = cluster.name
          zone           = cluster.zone
          pool_name      = pool.name
          gpu_type       = pool.gpu_type
          memory_gb      = pool.memory_gb
          bandwidth      = pool.network_bandwidth_gbps
          cost_per_hour  = pool.cost_per_hour
          node_count     = pool.node_count
        }
      ]
    ]
  ])
}

resource "null_resource" "aks_cluster" {
  for_each = {
    for rg in var.resource_groups :
    "${rg.name}" => rg
  }
  triggers = {
    resource_group = each.value.name
    region         = each.value.region
    cluster_count  = length(each.value.aks_clusters)
  }
}

resource "null_resource" "node_pool" {
  for_each = {
    for pool in local.flat_node_pools :
    "${pool.resource_group}-${pool.cluster_name}-${pool.pool_name}" => pool
  }
  triggers = {
    resource_group = each.value.resource_group
    region         = each.value.region
    cluster_name   = each.value.cluster_name
    zone           = each.value.zone
    pool_name      = each.value.pool_name
    gpu_type       = each.value.gpu_type
    memory_gb      = each.value.memory_gb
    bandwidth      = each.value.bandwidth
    cost_per_hour  = each.value.cost_per_hour
    node_count     = each.value.node_count
  }
}

output "node_pools" {
  value = local.flat_node_pools
}

