var gulp = require('gulp');
var mainBowerFiles = require('gulp-main-bower-files');
var concat = require('gulp-concat');
var uglify = require('gulp-uglify');
var minify = require('gulp-minify-css');
var gulpFilter = require('gulp-filter');
var addsrc = require('gulp-add-src');
var ngAnnotate = require('gulp-ng-annotate');
var connect = require('gulp-connect');
var modRewrite = require('connect-modrewrite');
var mode = require('gulp-mode')();
var replace = require('gulp-replace');
var htmlmin = require('gulp-htmlmin');
var proxy = require('proxy-middleware');

var jsFilter = gulpFilter('**/*.js', {restore: true});
var cssFilter = gulpFilter('**/*.css', {restore: true});

gulp.task('vendor', function() {
  return gulp.src('./bower.json')
    .pipe(mainBowerFiles())
    .pipe(jsFilter)
    .pipe(concat('vendor.js'))
    .pipe(mode.production(ngAnnotate()))
    .pipe(mode.production(uglify()))
    .pipe(gulp.dest('./corvus_web/static'))
    .pipe(jsFilter.restore)

    .pipe(cssFilter)
    .pipe(addsrc('./assets/bower_components/angular-material/angular-material.layouts.css'))
    .pipe(concat('vendor.css'))
    .pipe(mode.production(minify()))
    .pipe(gulp.dest('./corvus_web/static'));
});

gulp.task('appjs', function() {
  return gulp.src(['./assets/js/app.js', './assets/js/**/*.js'])
    .pipe(concat('app.js'))
    .pipe(mode.production(ngAnnotate()))
    .pipe(mode.production(uglify()))
    .pipe(gulp.dest('./corvus_web/static'));
});

gulp.task('appcss', function() {
  return gulp.src('./assets/css/**/*.css')
    .pipe(concat('style.css'))
    .pipe(mode.production(minify()))
    .pipe(gulp.dest('./corvus_web/static'));
});

gulp.task('html', function() {
  return gulp.src('./assets/template/**/*.html')
    .pipe(mode.production(htmlmin({collapseWhitespace: true,})))
    .pipe(gulp.dest('./corvus_web/static/template'))
    .pipe(connect.reload());
});

gulp.task('watch', function() {
  gulp.watch('./assets/js/**/*.js', ['appjs']);
  gulp.watch('./assets/css/**/*.css', ['appcss']);
  gulp.watch('./assets/template/**/*.html', ['html']);
});

gulp.task('tag', function() {
  var timestamp = (new Date()).getTime();

  return gulp.src(['./assets/template/index.html'])
    .pipe(replace(/(.*)src="(.*)\.js.*"/g, '$1src="$2.js?v=' + timestamp + '"'))
    .pipe(replace(/(.*)href="(.*)\.css.*"/g, '$1href="$2.css?v=' + timestamp + '"'))
    .pipe(gulp.dest('./assets/template'));
});

gulp.task('untag', function() {
  return gulp.src(['./assets/template/index.html'])
    .pipe(replace(/(.*)src="(.*\.js).*"/g, '$1src="$2"'))
    .pipe(replace(/(.*)href="(.*\.css).*"/g, '$1href="$2"'))
    .pipe(gulp.dest('./assets/template'));
});

gulp.task('default', ['vendor', 'appjs', 'appcss', 'html']);

// Dev
gulp.task('dev', ['default', 'watch'], function () {
  // Server
  connect.server({
    root: 'corvus_web',
    port: 3000,
    livereload: true,
    middleware: function (connect, opt) {
      var middlewares = [];
      try {
        middlewares = require('./proxy.json').map(function (opt) {
          return proxy(opt);
        });
      } catch (e) {
        console.warn('proxy.json not found');
      }
      middlewares.push(modRewrite(['^[^\\.]*$ /static/template/index.html [L]']));
      return middlewares;
    }
  });
  gulp.watch('./corvus_web/static/template/*.html', ['html']);
});
