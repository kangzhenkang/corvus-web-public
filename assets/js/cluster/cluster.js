(function() {
  'use strict';

  angular
    .module('corvus')
    .controller('ClusterController', ClusterController);

  /* @ngInject */
  function ClusterController($scope, $rootScope, $mdDialog, $state,
                             $stateParams, utils, notify, clusterService,
                             taskService, nodeService, proxyService,
                             cmdService) {
    var cluster = this;

    cluster.items = [];
    cluster.toggleNodes = toggleNodes;
    cluster.addNode = addNode;
    cluster.addProxy = addProxy;
    cluster.deleteCluster = deleteCluster;
    cluster.deleteNodes = deleteNodes;
    cluster.deleteProxies = deleteProxies;
    cluster.splitSlots = splitSlots;
    cluster.executeCommand = cmdService.popup;
    cluster.getNodes = getNodes;
    cluster.getProxies = getProxies;
    cluster.getRelation = getRelation;
    cluster.editCluster = editCluster;
    cluster.updateProxy = proxyService.openUpdate;
    cluster.registerProxy = proxyService.register;
    cluster.deregisterProxy = proxyService.deregister;
    cluster.loadMoreNodes = loadMoreNodes;
    cluster.refreshNodes = refreshNodes;
    cluster.displayStats = true;
    cluster.globalNav = $rootScope.globalNav;

    cluster.page = 1;
    cluster.totalPages = 0;

    var searchSpec = '';
    if ($stateParams.q) {
      cluster.filters = buildSearch($stateParams.q);
      searchSpec = $stateParams.q;
    }
    $rootScope.globalNav.search = searchSpec;

    $scope.$on('scrolled', onScroll);
    $scope.$watch('globalNav.search', search);
    activate(1, true);

    function activate(page, reset) {
      cluster.loadingClusters = true;
      clusterService.getClusters(page, cluster.filters)
        .then(function(response) {
          cluster.loadingClusters = false;

          var newItems = response.data.objects;
          cluster.totalPages = response.data.total_pages;
          cluster.page = response.data.page;

          angular.forEach(newItems, function(v) {
            v.node = {page: 1};

            v.selected = [];
            v.proxySelected = [];
            v.nodeCount = v.node_count;
            v.proxyCount = v.proxy_count;
            v.newFields = {
              'description': v.description,
              'register_app': v.register_app,
              'register_cluster': v.register_cluster,
            };

            v.editing = false;

            if (v.maxmemory && v.maxmemory > 0) {
              var d1 = v.memory / v.maxmemory;
              var d2 = v.hottest_node_mem_used / v.hottest_node_max_mem;
              if (d1 > 0.9 || d2 > 0.9) {
                v.memClass = 'label-red';
              } else if (d1 > 0.8 || d2 > 0.8) {
                v.memClass = 'label-yellow';
              } else {
                v.memClass = 'label-green';
              }
              v.memPercent = utils.formatPercent(v.memory, v.maxmemory);
              v.hottestNodeMemPercent = utils.formatPercent(v.hottest_node_mem_used, v.hottest_node_max_mem);
            }

            if (v.fail_nodes) {
              v.failNodeCount = v.fail_nodes.length;
              v.migratingNodeCount = v.migrating.length;
              v.missingSlots= v.missing_slots;
            } else {
              v.failNodeCount = 0;
              v.migratingNodeCount = 0;
              v.missingSlots = 0;
            }
          });
          if (reset) {
            cluster.items = [];
          }
          cluster.items = (cluster.items || []).concat(newItems);
        }, function(err) {
          cluster.loadingClusters = false;
          notify.warn(err.data.message);
        });
    }

    function getNodes(item, callback) {
      item.loadingNodes = true;

      nodeService.getNodes(item.page || 1, {
        filters: [{
          name: 'cluster_id',
          op: '==',
          val: item.id
        }]
      }).then(function(response) {
        item.loadingNodes = false;

        item.page = response.data.page;
        item.pages = response.data.total_pages;

        var nodes = response.data.objects;
        angular.forEach(nodes, function(n) {
          n.usedMemSpec = utils.formatBytes(n.usedMemory);
          n.maxMemSpec = utils.formatBytes(n.maxMemory);
          n.memClass = utils.getMemoryClass(n.usedMemory, n.maxMemory);
          n.memPercent = utils.formatPercent(n.usedMemory, n.maxMemory);
        });
        if (item.page === 1) {
          item.nodes = nodes;
        } else {
          item.nodes = (item.nodes || []).concat(nodes);
        }
        item.nodeCount = response.data.num_results;
        if (callback) {
          callback(item);
        }
      }, function(err) {
        item.loadingNodes = false;

        notify.warn(err.data.message);
      });
    }

    function refreshNodes(item) {
      item.page = 1;
      getNodes(item);
    }

    function loadMoreNodes(item) {
      item.page++;
      getNodes(item);
    }

    function getProxies(item) {
      item.loadingProxies = true;
      proxyService.getProxiesByCluster(item.id)
        .then(function(response) {
          item.loadingProxies = false;
          var proxies = response.data.objects;

          angular.forEach(response.data.objects, function(p) {
            p.statusClass = p.alive ? 'label-green' : 'label-red';
            p.disableUpdate = !p.canUpdate || !p.alive;
          });

          item.proxies = proxies;
          item.proxyCount = proxies.length;
        }, function(err) {
          item.loadingProxies = false;
          notify.warn(err.data.message);
        });
    }

    function toggleNodes(item) {
      if (item.showNodes) {
        item.showNodes = false;
        return;
      }

      if ((item.nodes || []).length <= 0) {
        getNodes(item);

        nodeService.getCount(item.id)
          .then(function(response) {
            item.masters = response.data.masters;
            item.slaves = response.data.slaves;
          }, function(err) {
            notify.warn(err.data.message);
          });
      }

      if ((item.proxies || []).length <= 0) {
        getProxies(item);
      }

      item.showNodes = true;
    }

    function addNode(item) {
      $mdDialog.show({
        templateUrl: '/static/template/node/add.html',
        controller: 'ClusterNodeController',
        controllerAs: 'clusterNode',
        bindToController: true,
        locals: {
          clusterId: item.id,
          clusterName: item.name,
          nodeCount: item.nodeCount,
        },
      });
    }

    function showProxyAddingDialog(item) {
      $mdDialog.show({
        templateUrl: '/static/template/proxy/create.html',
        controller: 'ClusterProxyController',
        controllerAs: 'clusterProxy',
        bindToController: true,
        locals: {
          clusterId: item.id,
          clusterName: item.name,
          proxyCount: item.proxyCount,
          nodes: item.nodes,
          reload: function() { getProxies(item); },
        }
      });
    }

    function addProxy(item) {
      if (!item.nodes) {
        getNodes(item, showProxyAddingDialog);
      } else {
        showProxyAddingDialog(item);
      }
    }

    function deleteCluster(item) {
      $mdDialog.show(
        utils.confirm('删除集群', '确定删除集群 ' + item.name + ' ?')
      ).then(function() {
        clusterService.deleteCluster(item.id)
          .then(function(response) {
            if (response.data.status === -1) {
              notify.warn(response.data.message);
            } else {
              taskService.notifyTask({taskId: response.data.task_id});
            }
          }, function(err) {
            notify.warn(err.data.message);
          });
      });
    }

    function deleteNodes(item) {
      var selected = item.selected;
      if (selected.length <= 0) {
        return;
      }

      var nodeAddress = [];
      var data = {clusterId: item.id, nodes: []};
      angular.forEach(selected, function(v) {
        nodeAddress.push([v.host, v.port].join(':'));
        data.nodes.push({host: v.host, port: v.port, nodeId: v.nodeId});
      });

      $mdDialog.show(
        utils.confirm('删除节点', '确定删除这些节点？' + nodeAddress.join(', '))
      ).then(function() {
        nodeService.quit(data)
          .then(function(response) {
            taskService.notifyTask({taskId: response.data.task_id});
          }, function(err) {
            notify.warn(err.data.message);
          });
      });
    }

    function deleteProxies(item) {
      var selected = item.proxySelected;
      if (selected.length <= 0) {
        return;
      }

      var proxyAddress = [];
      var data = {clusterId: item.id, proxies: []};
      angular.forEach(selected, function(v) {
        proxyAddress.push([v.host, v.port].join(':'));
        data.proxies.push(v.id);
      });

      $mdDialog.show(
        utils.confirm('删除代理', '确定删除这些代理？' + proxyAddress.join(', '))
      ).then(function() {
        clusterService.deleteProxies(data)
          .then(function(response) {
            if (response.data.status === -1) {
              notify.warn(response.data.message);
            } else {
              item.proxySelected = [];
              notify.notice('已创建删除任务');
            }
          }, function(err) {
            notify.warn(err.data.message);
          });
      });
    }

    function splitSlots(item) {
      if (item.nodes.length <= 0) {
        return;
      }

      $mdDialog.show(
        utils.confirm('', '确定均分槽位？')
      ).then(function() {
        var node = item.nodes[0];
        clusterService.splitSlots({
          host: node.host,
          port: node.port,
          clusterId: item.id
        }).then(function(response) {
          taskService.notifyTask({taskId: response.data.task_id});
        }, function(err) {
          notify.warn(err.data.message);
        });
      });
    }

    function getRelation(item) {
      $mdDialog.show({
        templateUrl: '/static/template/relation.html',
        controller: 'RelationController',
        controllerAs: 'relation',
        bindToController: true,
        locals: {
          clusterId: item.id,
          reload: function() { refreshNodes(item); }
        },
      });
    }

    function editCluster(item) {
      item.descEditing = false;
      item.appEditing = false;
      item.clusterEditing = false;
      if (item.newFields.description === item.description
        && item.newFields.register_app === item.register_app
        && item.newFields.register_cluster === item.register_cluster) {
        return;
      }
      item.description = item.newFields.description;
      item.register_app = item.newFields.register_app;
      item.register_cluster = item.newFields.register_cluster;
      clusterService.update(item.id, item.newFields).then();
    }

    function onScroll() {
      cluster.page++;
      if (cluster.page > cluster.totalPages) {
        return;
      }
      activate(cluster.page);
    }

    function buildSearch(value) {
      return {or: [
        {name: 'name', op: 'like', val: '%' + value + '%'},
        {name: 'description', op: 'like', val: '%' + value + '%'},
      ]};
    }

    function search(value, old) {
      if (value == old) { return; }

      value = value.trim();
      $state.go('cluster', {q: value}, {notify: false});

      cluster.filters = value ? buildSearch(value) : null;
      cluster.items = [];
      activate(1, true);
    }
  }
})();
