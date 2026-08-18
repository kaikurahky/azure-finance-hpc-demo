param accountName string
param deployPool bool
param poolName string
param location string
param tags object

resource batchAccount 'Microsoft.Batch/batchAccounts@2025-06-01' = {
  name: accountName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    allowedAuthenticationModes: [
      'AAD'
    ]
    poolAllocationMode: 'BatchService'
    publicNetworkAccess: 'Enabled'
  }
}

resource pool 'Microsoft.Batch/batchAccounts/pools@2025-06-01' = if (deployPool) {
  parent: batchAccount
  name: poolName
  tags: tags
  properties: {
    displayName: 'Finance Monte Carlo Low Priority Pool'
    vmSize: 'Standard_F8s_v2'
    deploymentConfiguration: {
      virtualMachineConfiguration: {
        imageReference: {
          publisher: 'canonical'
          offer: '0001-com-ubuntu-server-jammy'
          sku: '22_04-lts'
          version: 'latest'
        }
        nodeAgentSkuId: 'batch.node.ubuntu 22.04'
      }
    }
    scaleSettings: {
      autoScale: {
        evaluationInterval: 'PT5M'
        formula: '$NodeDeallocationOption = taskcompletion; $TargetDedicatedNodes = 0; $TargetLowPriorityNodes = min(10, max(0, $PendingTasks.GetSample(1)));'
      }
    }
    taskSlotsPerNode: 8
  }
}

output accountEndpoint string = batchAccount.properties.accountEndpoint
output accountId string = batchAccount.id
