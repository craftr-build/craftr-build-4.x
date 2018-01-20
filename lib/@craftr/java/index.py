"""
Targets for building Java projects.
"""

import copy
import nodepy
import re
import typing as t
import craftr, {path, options, utils} from 'craftr'
import maven from './maven'

ONEJAR_FILENAME = path.canonical(
  options.get('java.onejar',
  path.join(str(module.directory), 'one-jar-boot-0.97.jar')))


def _init_repos():
  repo_config = copy.deepcopy(options.get('java.maven_repos', {}))
  repo_config.setdefault('default', 'http://repo1.maven.org/maven2/')

  repos = []
  if repo_config['default']:
    repos.append(maven.MavenRepository('default', repo_config.pop('default')))
  for name, repo_url in repo_config.items():
    repos.append(maven.MavenRepository(name, repo_url))
  return repos

repos = _init_repos()


def partition_sources(
    sources: t.List[str],
    base_dirs: t.List[str],
    parent: str
  ) -> t.Dict[str, t.List[str]]:
  """
  Partitions a set of files in *sources* to the appropriate parent directory
  in *base_dirs*. If a file is found that is not located in one of the
  *base_dirs*, a #ValueError is raised.

  A relative path in *sources* and *base_dirs* will be automatically converted
  to an absolute path using the *parent*, which defaults to the currently
  executed module's directory.
  """

  base_dirs = [path.canonical(x, parent) for x in base_dirs]
  result = {}
  for source in [path.canonical(x, parent) for x in sources]:
    for base in base_dirs:
      rel_source = path.rel(source, base)
      if path.isrel(rel_source):
        break
    else:
      raise ValueError('could not find relative path for {!r} given the '
        'specified base dirs:\n  '.format(source) + '\n  '.join(base_dirs))
    result.setdefault(base, []).append(rel_source)
  return result


class _JarProducingMixin:

  def init(self, jar_dir=None, jar_name=None, main_class=None, javac_jar=None):
    if jar_dir:
      jar_dir = path.canonical(self.jar_dir, self.namespace.build_directory)
    self.jar_dir = jar_dir
    self.jar_name = jar_name
    self.main_class = main_class
    self.javac_jar = javac_jar or options.get('java.javac_jar', 'jar')
    if not self.jar_dir:
      self.jar_dir = self.namespace.build_directory
    if not self.jar_name:
      self.jar_name = (self.namespace.name.split('/')[-1] + '-' + self.target.name + '-' + self.namespace.version)

  @property
  def jar_filename(self) -> str:
    if path.isabs(self.jar_name):
      return self.jar_name
    return path.join(self.jar_dir, self.jar_name) + '.jar'


class JavaLibrary(craftr.Behaviour, _JarProducingMixin):

  def init(self, srcs, src_roots=None, class_dir=None, javac=None,
           extra_arguments=None, **kwargs):
    kwargs = utils.call_with_signature(_JarProducingMixin.init, self, **kwargs)
    utils.raise_unexpected_kwarg(kwargs)

    if src_roots is None:
      src_roots = options.get('java.src_roots', ['src', 'java', 'javatest'])
    if src_roots:
      src_roots = [craftr.localpath(x) for x in src_roots]

    self.srcs = [craftr.localpath(x) for x in srcs]
    self.src_roots = src_roots
    self.class_dir = class_dir
    self.javac = javac or options.get('java.javac', 'javac')
    self.extra_arguments = extra_arguments
    if not self.class_dir:
      self.class_dir = 'classes/' + self.target.name
    self.class_dir = path.canonical(self.class_dir, self.namespace.build_directory)

  def translate(self, jar_filename=None):
    jar_filename = jar_filename or self.jar_filename
    extra_arguments = options.get('java.extra_arguments', []) + (self.extra_arguments or [])
    classpath = []

    for target in self.target.deps(with_behaviour=JavaLibrary):
      classpath.append(target.impl.jar_filename)
    for target in self.target.deps(with_behaviour=JavaPrebuilt):
      classpath.extend(target.impl.binary_jars)

    # Calculate output files.
    classfiles = []
    for base, sources in partition_sources(self.srcs, self.src_roots, self.namespace.directory).items():
      for src in sources:
        classfiles.append(path.join(self.class_dir, path.setsuffix(src, '.class')))

    if self.srcs:
      command = [self.javac, '-d', self.class_dir]
      if classpath:
        command += ['-classpath', path.pathsep.join(classpath)]
      command += self.srcs
      command += extra_arguments

      self.target.add_action(
        name = 'javac',
        commands = [command],
        input_files = classpath + self.srcs,
        output_files = classfiles
      )

    flags = 'cvf'
    if self.main_class:
      flags += 'e'

    command = [self.javac_jar, flags, jar_filename]
    if self.main_class:
      command.append(self.main_class)
    command += ['-C', self.class_dir, '.']

    self.target.add_action(
      name = 'jar',
      commands = [command],
      input_files = classfiles,
      output_files = [jar_filename]
    )


class JavaBinary(craftr.Behaviour, _JarProducingMixin):
  """
  Takes a list of Java dependencies and creates an executable JAR archive
  from them.

  # Parameters
  dist_type:
    The distribution type. Can be `'merge'`, `'onejar'` or `None`. The default
    is the value configured in `java.dist_type` (which defaults to `'merge'`).
  """

  def init(self, main_class=None, dist_type=NotImplemented, **kwargs):
    kwargs = utils.call_with_signature(_JarProducingMixin.init, self, **kwargs)

    if not main_class:
      raise ValueError('missing value for "main_class"')
    if dist_type not in ('merge', 'onejar', None, NotImplemented):
      raise ValueError('invalid dist_type: {!r}'.format(dist_type))
    self.main_class = main_class
    self.dist_type = dist_type
    self.library = None

    if kwargs.get('srcs'):
      if self.dist_type is None:
        kwargs['jar_name'] = self.jar_filename
      else:
        kwargs['jar_name'] = path.addtobase(self.jar_filename, '-classes')
      self.library = library(name='lib', parent=self.target, **kwargs)

  def translate(self):
    if self.dist_type is NotImplemented:
      self.dist_type = options.get('java.dist_type', 'merge')

    inputs = []
    if self.library:
      self.library.translate()
      inputs.append(self.library.impl.jar_filename)

    if self.dist_type is None:
      return

    for target in self.target.deps(with_behaviour=JavaLibrary):
      inputs.append(target.impl.jar_filename)
    for target in self.target.deps(with_behaviour=JavaPrebuilt):
      inputs.extend(target.impl.binary_jars)

    command = nodepy.runtime.exec_args + [str(require.resolve('./augjar').filename)]
    command += ['-o', self.jar_filename]

    if self.dist_type == 'merge':
      command += [inputs[0]]  # Merge into the first specified dependency.
      command += ['-s', 'Main-Class=' + self.main_class]
      for infile in inputs[1:]:
        command += ['-m', infile]

    else:
      assert self.dist_type == 'onejar'
      command += [ONEJAR_FILENAME]
      command += ['-s', 'One-Jar-Main-Class=' + self.main_class]
      for infile in inputs:
        command += ['-f', 'lib/' + path.base(infile) + '=' + infile]

    self.target.add_action(
      name = self.dist_type,
      commands = [command],
      input_files = inputs,
      output_files = [self.jar_filename]
    )


class JavaPrebuilt(craftr.Behaviour):
  """
  Represents a prebuilt JAR. If an artifact ID is specified, the artifact will
  be downloaded from Maven Central, or the configured maven repositories.

  # Parameters
  binary_jar:
    The path to a binary `.jar` file.
  artifact:
    An artifact ID of the format `group:artifact:version` which will be
    downloaded from Maven.
  """

  def init(self, binary_jars=None, artifacts=None):
    if not binary_jars:
      binary_jars = []
    if not artifacts:
      artifacts = []

    self.artifacts = [maven.Artifact.from_id(x) for x in artifacts]
    self.binary_jars = [craftr.localpath(x) for x in binary_jars]
    self.did_install = False

  def install(self):
    """
    Download the artifacts from the repository and add the binary JAR files
    to the #binary_jars list.
    """

    if self.did_install:
      return
    self.did_install = True

    poms = {}
    queue = [(0, x) for x in reversed(self.artifacts)]

    # XXX This should probably be compared against a global set of already
    #     installed dependencies, so we don't do the same work twice if
    #     two separate projects need the same dependency.

    print('[{}] Resolving JARs...'.format(self.target.long_name))
    while queue:
      depth, artifact = queue.pop()
      if artifact.scope != 'compile' or artifact.type != 'jar':
        continue

      # For now, we use this to avoid downloading the same dependency in
      # different versions, instead only the first version that we find.
      artifact_id = '{}:{}'.format(artifact.group, artifact.artifact)
      if artifact_id in poms:
        continue

      # Try to find a POM manifest for the artifact.
      for repo in repos:
        # If the artifact has no version, that version may be filled in by
        # the repository, but we only want to use that filled in version if
        # we can get a POM.
        artifact_clone = copy.copy(artifact)
        pom = repo.download_pom(artifact_clone)
        if pom:
          artifact = artifact_clone
          break
      else:
        if not artifact.optional:
          raise RuntimeError('could not find artifact: {}'.format(artifact))
        print(indent[:-2] + '    SKIP (Optional)')
        continue

      # Cache the POM and add its dependencies so we can "recursively"
      # resolve them.
      poms[artifact_id] = (artifact, pom, repo)
      queue.extend([(depth+1, x) for x in reversed(maven.pom_eval_deps(pom))])

      # Print dependency info.
      indent = '| ' * depth
      print('  {}{} ({})'.format('| ' * depth, artifact, repo.name))

    # Download dependencies.
    for artifact, pom, repo in poms.values():
      binary_jar = path.join(craftr.build_directory, '.maven-artifacts', artifact.to_local_path('jar'))
      self.binary_jars.append(binary_jar)

      # Create a download action. We may create actions even before
      # #translate(), so we save ourselves some trouble.
      command = nodepy.runtime.exec_args + [
        str(require.resolve('craftr/tools/download').filename),
        '--url', repo.get_artifact_uri(artifact, 'jar'),
        '--to', binary_jar
      ]
      self.target.add_action(
        name = str(artifact),
        commands = [command],
        output_files = [binary_jar]
      )

  def translate(self):
    self.install()


class JavaProguard(craftr.Behaviour):
  """
  Run ProGuard on the JAR dependencies of this target. If the *pro_file*
  argument is specified, it must be the name of a response file that will
  be passed to the ProGuard commandline.

  The *cwd* will default to the parent directory of *pro_file*, if specified.
  """

  def init(self, pro_file=None, options=(), cwd=None, java=None, outjars=None):
    self.java = java or options.get('java.java', 'java')
    self.pro_file = craftr.localpath(pro_file) if pro_file else None
    if not cwd and self.pro_file:
      cwd = path.dir(self.pro_file)
    self.cwd = craftr.localpath(cwd) if cwd else None
    self.options = options
    self.outjars = outjars

  def translate(self):
    injars = []
    for target in self.target.deps(with_behaviour=prebuilt):
      injars.append(target.impl.binary_jar)
    for target in self.target.deps(with_behaviour=library):
      injars.append(target.impl.jar_filename)

    if self.outjars:
      outjars = self.outjars
    else:
      outjars = [path.canonical(path.addtobase(x, '.proguard')) for x in injars]

    args = [self.java, '-jar', str(module.directory.joinpath('proguard-5.3.3.jar'))]
    if self.pro_file:
      args.append('@' + self.pro_file)
    args += ['-injars', path.pathsep.join(injars)]
    args += ['-outjars', path.pathsep.join(outjars)]
    # XXX -libraryjars for all transitive dependencies?
    # XXX rt.jar no longer available in Java 9
    args += ['-libraryjars', '<java.home>/lib/rt.jar']
    args += self.options

    self.target.add_action(
      commands = [args],
      input_files = injars,
      output_files = outjars,
      cwd = self.cwd
    )


def run(binary, *argv, name=None, java=None, jvm_args=(), **kwargs):
  kwargs.setdefault('explicit', True)
  kwargs.setdefault('console', True)
  target = craftr.resolve_target(binary)
  if name is None:
    name = target.name + '_run'
  if java is None:
    java = options.get('java.java', 'java')
  command = [java] + list(jvm_args) + ['-jar', target.impl.jar_filename] + list(argv)
  return craftr.gentarget(name = name, deps = [target], commands = [command], **kwargs)


library = craftr.Factory(JavaLibrary)
binary = craftr.Factory(JavaBinary)
prebuilt = craftr.Factory(JavaPrebuilt)
proguard = craftr.Factory(JavaProguard)
