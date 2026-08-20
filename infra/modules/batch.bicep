param accountName string
param deployPool bool
param autoscalePoolName string
param alwaysOnPoolName string
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
    encryption: {
      keySource: 'Microsoft.Batch'
    }
    poolAllocationMode: 'BatchService'
    publicNetworkAccess: 'Enabled'
  }
}

resource autoscalePool 'Microsoft.Batch/batchAccounts/pools@2025-06-01' = if (deployPool) {
  parent: batchAccount
  name: autoscalePoolName
  tags: tags
  properties: {
    displayName: 'Finance Monte Carlo Low Priority Pool'
    vmSize: 'STANDARD_F8S_V2'
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
    taskSchedulingPolicy: {
      jobDefaultOrder: 'None'
      nodeFillType: 'Spread'
    }
  }
}

resource alwaysOnPool 'Microsoft.Batch/batchAccounts/pools@2025-06-01' = if (deployPool) {
  parent: batchAccount
  name: alwaysOnPoolName
  tags: tags
  properties: {
    displayName: 'Finance Monte Carlo Always-On Low Priority Pool'
    vmSize: 'STANDARD_F8S_V2'
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
      fixedScale: {
        targetDedicatedNodes: 0
        targetLowPriorityNodes: 10
      }
    }
    taskSlotsPerNode: 8
  }
}

output accountEndpoint string = batchAccount.properties.accountEndpoint
output accountId string = batchAccount.id
