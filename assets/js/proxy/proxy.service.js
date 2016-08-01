(function() {
  'use strict';

  angular
    .module('corvus')
    .service('proxyService', ProxyService);

  /* @ngInject */
  function ProxyService($http, $mdDialog, notify, utils) {
    this.getProxiesByCluster = getProxiesByCluster;
    this.info = info;
    this.update = update;
    this.updateAll = updateAll;
    this.create = create;
    this.add = add;
    this.getProxyList = getProxyList;
    this.openUpdate = openUpdate;
    this.register = register;
    this.registerAll = registerAll;
    this.deregister = deregister;

    function getProxiesByCluster(clusterId) {
      var filters = {filters: [{name: 'cluster_id', op: '==', val: clusterId}]};
      return $http.get('/api/proxy', {
        params: {
          q: JSON.stringify(filters),
          results_per_page: 16384,
        }
      });
    }

    function info(host, port) {
      return $http.get('/api/remote/proxy/info/' + host + '/' + port);
    }

    function update(data) {
      return $http.post('/api/remote/proxy/update', data);
    }

    function create(model, callback) {
      if (!model.host) {
        notify.warn('代理主机地址没有填写');
        return;
      }
      if (!model.config.bind) {
        notify.warn('代理端口没有填写');
        return;
      }

      if (!model.config.node) {
        notify.warn('集群节点没有填写');
        return;
      }

      if (!model.config.version) {
        notify.warn('代理版本没有填写');
        return;
      }

      model.submitting = false;
      $http.post('/api/remote/proxy/create', {clusterId: model.clusterId,
                 host: model.host, config: model.config})
        .then(function(response) {
          if (response.data.status === -1) {
            notify.warn(response.data.message);
          } else {
            callback(response.data);
          }
          model.submitting = false;
        }, function(err) {
          notify.warn(err.data.message);
          model.submitting = false;
        });
    }

    function add(entries, model, callback) {
      var nodes = utils.getAddresses(entries);
      if (nodes.length <= 0) {
        notify.warn('添加节点后再提交');
        return;
      }

      model.submitting = true;
      $http.post('/api/proxy/add', {clusterId: model.clusterId, proxies: nodes})
        .then(function(response) {
          if (response.data.status == -1) {
            notify.warn(response.data.message);
          } else {
            callback();
          }
          model.submitting = false;
      }, function(err) {
        notify.warn(err.data.message);
        model.submitting = false;
      });
    }

    function getProxyList(model, page, callback) {
      var params = {page: page};
      if (model.cluster) {
        params.cluster = model.cluster;
      }
      if (model.version) {
        params.version = model.version;
      }

      if (model.registered) {
        if (['false', 'no', '0'].indexOf(model.registered) !== -1) {
          params.registered = false;
        } else {
          params.registered = true;
        }
      }

      model.loading = true;
      $http.get('/api/proxy/list', {params: params})
      .then(function(response) {
        if (response.data.status === -1) {
          notify.warn(response.data.message);
        } else {
          if (callback) {
            callback(response.data);
          }
        }
        model.loading = false;
      }, function(err) {
        notify.warn(err.data.message);
        model.loading = false;
      });
    }

    function updateAll(model, newVersion, cluster, version, registered, callback) {
      var data = {newVersion: newVersion};
      if (version) {
        data.version = version;
      }
      if (cluster) {
        data.cluster = cluster;
      }
      if (registered) {
        data.registered = registered;
      }
      model.submitting = true;
      $http.post('/api/proxy/updateAll', data)
        .then(function(response) {
          if (response.data.status == -1) {
            notify.warn(response.data.message);
          } else {
            if (callback) {
              callback(response.data);
            }
          }
          model.submitting = false;
        }, function(err) {
          notify.warn(err.data.message);
          model.submitting = false;
        });
    }

    function openUpdate(proxy) {
      proxy.loading = true;
      info(proxy.host, proxy.port).then(function(response) {
        proxy.loading = false;
        if (response.data.status === -1) {
          notify.warn(response.data.message);
        } else {
          $mdDialog.show({
            templateUrl: '/static/template/proxy/update.html',
            controller: 'ProxyUpdateController',
            controllerAs: 'proxyUpdate',
            bindToController: true,
            locals: {
              config: response.data.conf,
              host: proxy.host,
              port: proxy.port,
              clusterId: proxy.cluster_id
            }
          });
        }
      }, function(err) {
        proxy.loading = false;
        notify.warn(err.data.message);
      });
    }

    function register(data, cluster) {
      data.registering = true;
      data.register_app = cluster.register_app;
      data.register_cluster = cluster.register_cluster;
      $http.post('/api/proxy/register', data)
        .then(function(response) {
          data.registering = false;
          if (response.data.status === -1) {
            notify.warn(response.data.message);
          } else {
            notify.notice('代理已成功注册');
            data.registered = true;
          }
        }, function(err) {
          data.registering = false;
          notify.warn(err.data.message);
        });
    }

    function registerAll(data) {
      return $http.post('/api/proxy/registerAll', data);
    }

    function deregister(data) {
      data.deregistering = true;
      $mdDialog.show(
        utils.confirm('', '确定要从 huskar 删除代理 ' + data.host + ':' + data.port + ' 吗？')
      ).then(function() {
        $http.post('/api/proxy/deregister', data)
          .then(function(response) {
            data.deregistering = false;
            if (response.data.status === -1) {
              notify.warn(response.data.message);
            } else {
              notify.notice('代理已成功从 huskar 删除');
              data.registered = false;
            }
          }, function(err) {
            data.deregistering = false;
            notify.warn(err.data.message);
          });
      }, function() {
        data.deregistering = false;
      });
    }
  }
})();
