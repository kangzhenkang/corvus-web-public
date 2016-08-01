(function() {
  'use strict';

  angular
    .module('corvus')
    .service('githubApi', GithubApi);

  /* @ngInject */
  function GithubApi($http) {
    var uri = 'https://api.github.com/repos/eleme/corvus/releases/latest';
    var etagName = 'corvus-github-etag';
    var version = 'corvus-github-version';

    this.getRelease = getRelease;

    function getRelease(callback) {
      var config = {headers: {}};
      var etag = localStorage[etagName];
      if (etag) {
        config.headers['If-None-Match'] = etag;
      }
      $http.get(uri, config)
        .then(function(response) {
          var v = response.data.name.substr(1);
          localStorage[version] = v;
          localStorage[etagName] = response.headers('ETag');
          callback(v);
        }, function(response) {
          if (response.status == 304) {
            localStorage[etagName] = response.headers('ETag');
            callback(localStorage[version] || '');
          }
        });
    }
  }
})();
