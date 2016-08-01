(function() {
  'use strict';

  angular
    .module('corvus')
    .controller('NodeController', NodeController);

  /* @ngInject */
  function NodeController($scope, $rootScope, $state, $stateParams,
                          $mdDialog, utils, notify, nodeService, cmdService) {
    var node = this;

    node.items = [];
    node.popupReshard = nodeService.popupReshard;
    node.quitCluster = nodeService.quitCluster;
    node.remove = remove;
    node.executeCommand = cmdService.popup;

    node.totalPages = 0;
    node.page = 1;
    node.filters = null;

    var searchSpec = '';
    if ($stateParams.q) {
      node.filters = buildSearch($stateParams.q);
      searchSpec = $stateParams.q;
    }
    $rootScope.globalNav.search = searchSpec;

    $scope.$on('scrolled', onScroll);
    $scope.$watch('globalNav.search', search);
    activate(1, true);

    function activate(page, reset) {
      node.loadingNodes = true;

      nodeService.getNodes(page, node.filters)
        .then(function(response) {
          node.loadingNodes = false;

          var newItems = response.data.objects;
          node.totalPages = response.data.total_pages;
          node.page = response.data.page;

          angular.forEach(newItems, function(v) {
            v.usedMemSpec = utils.formatBytes(v.usedMemory);
            v.maxMemSpec = utils.formatBytes(v.maxMemory);
            v.memClass = utils.getMemoryClass(v.usedMemory, v.maxMemory);
            v.memPercent = utils.formatPercent(v.usedMemory, v.maxMemory);
          });
          if (reset) {
            node.items = [];
          }
          node.items = (node.items || []).concat(newItems);
          // list idle nodes first
          var idles = [], not_idles = [];
          for (var i = 0; i < node.items.length; i++) {
            if (node.items[i].idle) {
              idles.push(node.items[i]);
            } else {
              not_idles.push(node.items[i]);
            }
          }
          node.items = idles.concat(not_idles);
        }, function(err) {
          node.loadingNodes = false;
          notify.warn(err.data.message);
        });
    }

    function remove(item) {
      $mdDialog.show(
        utils.confirm('', '确定移除节点 ' + item.host + ':' + item.port + '？')
      ).then(function() {
        nodeService.remove(item.nodeId)
          .then(function(response) {
            if (response.data.status === -1) {
              notify.warn(response.data.message);
            } else {
              notify.notice('成功删除');
              $state.go($state.current, {}, {reload: true});
            }
          }, function(err) {
            notify.warn(err.data.message);
          });
      });
    }

    function onScroll() {
      node.page++;
      if (node.page > node.totalPages) {
        return null;
      }
      activate(node.page);
    }

    function buildSearch(value) {
      var filter = {filters: []};
      var components = value.split(':');
      var portFilter = null;
      var hostFilter = null;
      var state = null;

      switch (components.length) {
        case 1:
          var field = components[0].trim();
          if (!field) { return null; }

          hostFilter = {name: 'host', op: 'like', val: '%' + field + '%'};
          portFilter = {name: 'port', op: 'like', val: '%' + field + '%'};
          state = {name: 'cluster_id', op: '==', val: -1};

          if (!isNaN(Number(field))) {
            filter.filters.push({or: [hostFilter, portFilter]});
          } else if (field === 'idle') {
            filter.filters.push(state);
          } else {
            filter.filters.push(hostFilter);
          }
          break;
        case 2:
          var host = components[0].trim();
          var port = components[1].trim();
          hostFilter = {name: 'host', op: 'like', val: '%' + host + '%'};
          portFilter = {name: 'port', op: 'like', val: '%' + port + '%'};

          if (host && port) {
            filter.filters.push({and: [hostFilter, portFilter]});
          } else if (host) {
            filter.filters.push(hostFilter);
          } else if (port) {
            filter.filters.push(portFilter);
          } else {
            return null;
          }
          break;
        default: return null;
      }
      return filter;
    }

    function search(value, old) {
      if (value === old) { return; }
      value = value.trim();
      $state.go('node', {q: value}, {notify: false});

      node.filters = value ? buildSearch(value) : null;
      node.items = [];
      activate(1, true);
    }
  }
})();
