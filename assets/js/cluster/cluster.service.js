(function() {
  'use strict';

  angular
    .module('corvus')
    .service('clusterService', ClusterService);

  /* @ngInject */
  function ClusterService($http, $mdDialog) {
    this.createCluster = createCluster;
    this.getClusters = getClusters;
    this.getCluster = getCluster;
    this.getClusterByHost = getClusterByHost;
    this.reshard = reshard;
    this.splitSlots = splitSlots;
    this.popupReshard = popupReshard;
    this.addCluster = addCluster;
    this.deleteCluster = deleteCluster;
    this.deleteProxies = deleteProxies;
    this.getRelation = getRelation;
    this.update = update;
    this.updateNodeList = updateNodeList;

    function createCluster(data) {
      return $http.post('/api/cluster/create', data);
    }

    function getClusters(page, filters, numResults) {
      var deletedFilter = {name: 'deleted', op: '!=', val: true};
      var params = {page: page, q: {filters: []}};
      if (filters) {
        params.q.filters.push({and: [deletedFilter, filters]});
      } else {
        params.q.filters.push(deletedFilter);
      }

      if (numResults) {
        params.results_per_page = numResults;
      }
      return $http.get('/api/cluster', {params: params});
    }

    function getCluster(clusterId) {
      return $http.get('/api/cluster/' + clusterId);
    }

    function getClusterByHost(host, port) {
      return $http.get('/api/cluster/' + host + '/' + port);
    }

    function addCluster(host, port, data) {
      return $http.post('/api/cluster/' + host + '/' + port, data);
    }

    function deleteCluster(clusterId) {
      return $http.post('/api/cluster/delete/' + clusterId);
    }

    function reshard(data) {
      return $http.post('/api/cluster/migrate', data);
    }

    function splitSlots(data) {
      return $http.post('/api/cluster/reshard', data);
    }

    function deleteProxies(data) {
      return $http.post('/api/remote/proxy/delete', data);
    }

    function getRelation(clusterId) {
      return $http.get('/api/cluster/info/' + clusterId);
    }

    function update(clusterId, data) {
      return $http.put('/api/cluster/' + clusterId, data);
    }

    function updateNodeList(clusterId, data, callback) {
      return $http.put('/api/node/update/' + clusterId, data);
    }

    function popupReshard(locals) {
      $mdDialog.show({
        templateUrl: '/static/template/reshard.html',
        controller: 'ReshardController',
        controllerAs: 'reshard',
        bindToController: true,
        locals: locals,
      });
    }
  }
})();
