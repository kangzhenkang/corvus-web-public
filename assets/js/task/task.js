(function() {
  'use strict';

  angular
    .module('corvus')
    .controller('TaskController', TaskController);

  /* @ngInject */
  function TaskController($scope, taskService, notify, utils) {
    var task = this;

    task.items = [];
    task.getStatus = taskService.getStatus;
    task.onPaginate = onPaginate;
    task.page = 1;
    task.itemCount = 0;
    task.filters = null;

    $scope.$watch('globalNav.search', search);
    activate(1);

    function getItems(objects) {
      task.items = [];
      angular.forEach(objects, function(v) {
        task.items.push({
          id: v.id,
          operation: v.operation,
          createAt: utils.formatDate(v.created_at),
          updateAt: utils.formatDate(v.updated_at),
          statusLabel: taskService.getStatusLabel(v.status),
          statusClass: taskService.getStatusClass(v.status),
        });
      });
    }

    function activate(page, filters) {
      task.loading = true;
      taskService.getTasks(page, filters)
        .then(function(response) {
          task.loading = false;
          getItems(response.data.objects);
          task.itemCount = response.data.num_results;
        }, function(err) {
          task.loading = false;
          notify.warn(err.data.message);
        });
    }

    function onPaginate(page, limit) {
      activate(page, task.filters);
    }

    function search(value, old) {
      task.filters = null;
      if (value == old) { return; }

      value = value.trim();
      if (!value) {
        activate(1);
        return;
      }

      var filter = {filters: [{name: 'operation', op: 'like', val: '%' + value + '%'}]};
      task.filters = filter;
      activate(1, filter);
    }
  }
})();
