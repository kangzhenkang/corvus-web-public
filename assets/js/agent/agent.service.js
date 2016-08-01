(function() {
  'use strict';

  angular
    .module('corvus')
    .service('agentService', AgentService);

  /* @ngInject */
  function AgentService($http, notify) {
    var agentService = this;

    agentService.add = add;
    agentService.update = update;
    agentService.getAgentList = getAgentList;
    agentService.updateAll = updateAll;

    function add(data) {
      return $http.post('/api/agent/add', data);
    }

    function update(model, data, callback) {
      model.submitting = true;
      $http.post('/api/remote/agent/update', data)
      .then(function(response) {
        if (response.data.status === -1) {
          notify.warn(response.data.message);
        } else if (callback) {
          callback(response.data);
        }
        model.submitting = false;
      }, function(err) {
        notify.warn(err.data.message);
        model.submitting = false;
      });
    }

    function getAgentList(model, page, callback) {
      var params = {page: page};
      if (model.host) {
        params.host = model.host;
      }

      model.loading = true;
      $http.get('/api/agent/list', {params: params})
      .then(function(response) {
        if (response.data.status === -1) {
          notify.warn(response.data.message);
        } else if (callback) {
          callback(response.data);
        }
        model.loading = false;
      }, function(err) {
        notify.warn(err.data.message);
        model.loading = false;
      });
    }

    function updateAll(model, newVersion, host, callback) {
      var data = {newVersion: newVersion};
      if (host) {
        data.host = host;
      }
      model.submitting = true;
      $http.post('/api/agent/updateAll', data)
        .then(function(response) {
          if (response.data.status == -1) {
            notify.warn(response.data.message);
          } else if (callback) {
            callback(response.data);
          }
          model.submitting = false;
        }, function(err) {
          notify.warn(err.data.message);
          model.submitting = false;
        });
    }
  }
})();
