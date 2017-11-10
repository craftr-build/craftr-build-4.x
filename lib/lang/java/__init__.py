"""
Targets for building Java projects.
"""

import copy
import nodepy
import re
import typing as t

import craftr, {path, session} from 'craftr'
import {NamedObject} from 'craftr/utils/types'
import maven from './maven'


ONEJAR_FILENAME = path.canonical(
  session.config.get('java.onejar',
  path.join(str(module.directory), 'one-jar-boot-0.97.jar')))


def _init_repos():
  repo_config = copy.deepcopy(session.config.get('java.maven_repos', {}))
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


class JavaBase(craftr.target.TargetData):
  """
  jar_dir:
    The directory where the jar will be created in.

  jar_name:
    The name of the JAR file. Defaults to the target name. Note that the Java
    JAR command does not support dots in the output filename, thus it will
    be rendered to a temporary directory.

  main_class:
    A classname that serves as an entry point for the JAR archive. Note that
    you should prefer to use `java_binary()` to create a JAR binary that
    contains all its dependencies merged into one.

  javac_jar:
    The name of Java JAR command to use. If not specified, defaults to the
    value of the `java.javac_jar` option or simply "jar".
  """

  def __init__(self, jar_dir: str = None,
                     jar_name: str = None,
                     main_class: str = None,
                     javac_jar: str = None):
    if jar_dir:
      jar_dir = path.canonical(self.jar_dir, self.cell.builddir)
    self.jar_dir = jar_dir
    self.jar_name = jar_name
    self.main_class = main_class
    self.javac_jar = javac_jar or session.config.get('java.javac_jar', 'jar')

  def mounted(self, target):
    super().mounted(target)
    cell = target.cell
    if not self.jar_dir:
      self.jar_dir = cell.builddir
    if not self.jar_name:
      self.jar_name = (cell.name.split('/')[-1] + '-' + target.name + '-' + cell.version)

  @property
  def jar_filename(self) -> str:
    return path.join(self.jar_dir, self.jar_name) + '.jar'


class JavaLibrary(JavaBase):
  """
  The base target for compiling Java source code and creating a Java binary
  or libary JAR file.

  # Parameters
  srcs:
    A list of source files. If `srcs_root` is not specified, the config option
    `java.src_roots` to determine the root of the source files.

  src_roots:
    A list of source root directories. Defaults to `java.src_roots` config.
    The default value for this configuration is `['src', 'java', 'javatest']`.

  class_dir:
    The directory where class files will be compiled to.

  javac:
    The name of Java compiler to use. If not specified, defaults to the value
    of the `java.javac` option or simply "javac".

  extra_arguments:
    A list of additional arguments for the Java compiler. They will be
    appended to the ones specified in the configuration.
  """

  def __init__(self, srcs: t.List[str],
                     src_roots: t.List[str] = None,
                     class_dir: str = None,
                     javac: str = None,
                     extra_arguments: t.List[str] = None,
                     **kwargs):
    super().__init__(**kwargs)

    if src_roots is None:
      src_roots = session.config.get('java.src_roots', ['src', 'java', 'javatest'])
    if src_roots:
      src_roots = [craftr.localpath(x) for x in src_roots]

    self.srcs = [craftr.localpath(x) for x in srcs]
    self.src_roots = src_roots
    self.class_dir = class_dir
    self.javac = javac or session.config.get('java.javac', 'javac')
    self.extra_arguments = extra_arguments

  def mounted(self, target):
    super().mounted(target)
    if not self.class_dir:
      self.class_dir = 'classes/' + target.name
    self.class_dir = path.canonical(self.class_dir, target.cell.builddir)

  def translate(self, target, jar_filename=None):
    jar_filename = jar_filename or self.jar_filename
    extra_arguments = session.config.get('java.extra_arguments', []) + (self.extra_arguments or [])
    classpath = []

    for data in target.deps().attr('data').of_type(JavaLibrary):
      classpath.append(data.jar_filename)
    for data in target.deps().attr('data').of_type(JavaPrebuilt):
      classpath.append(data.binary_jar)

    # Calculate output files.
    classfiles = []
    for base, sources in partition_sources(self.srcs, self.src_roots, target.cell.directory).items():
      for src in sources:
        classfiles.append(path.join(self.class_dir, path.setsuffix(src, '.class')))

    if self.srcs:
      command = [self.javac, '-d', self.class_dir]
      if classpath:
        command += ['-classpath', path.pathsep.join(classpath)]
      command += self.srcs
      command += extra_arguments

      mkdir = craftr.actions.Mkdir.new(
        target,
        name = 'mkdir',
        deps = [],
        directory = self.class_dir
      )
      javac = craftr.actions.System.new(
        target,
        name = 'javac',
        deps = [mkdir, ...],
        commands = [command],
        input_files = self.srcs,
        output_files = classfiles
      )
    else:
      javac = None

    flags = 'cvf'
    if self.main_class:
      flags += 'e'

    command = [self.javac_jar, flags, jar_filename]
    if self.main_class:
      command.append(self.main_class)
    command += ['-C', self.class_dir, '.']

    mkdir = craftr.actions.Mkdir.new(
      target,
      name = 'jar_dir',
      deps = [],
      directory = self.jar_dir
    )
    craftr.actions.System.new(
      target,
      name = 'jar',
      deps = [javac, mkdir, ...] if javac else [mkdir, ...],
      commands = [command],
      input_files = classfiles,
      output_files = [jar_filename]
    )


class JavaBinary(JavaLibrary):
  """
  Takes a list of Java dependencies and creates an executable JAR archive
  from them.

  # Parameters
  dist_type:
    The distribution type. Can be `'merge'` or `'onejar'`. The default is
    the value configured in `java.dist_type` or `'onejar'`
  """

  def __init__(self, main_class: str = None,
                     dist_type: str = None,
                     **kwargs):
    super().__init__(**kwargs)
    if not main_class:
      raise ValueError('missing value for "main_class"')
    if not dist_type:
      dist_type = session.config.get('java.dist_type', 'onejar')
    if dist_type not in ('merge', 'onejar'):
      raise ValueError('invalid dist_type: {!r}'.format(self.dist_type))
    self.main_class = main_class
    self.dist_type = dist_type

  def translate(self, target):
    inputs = []

    if self.srcs:
      sub_jar = path.addtobase(self.jar_filename, '-classes')
      super().translate(target, jar_filename=sub_jar)
      inputs.append(sub_jar)

    for data in target.deps().attr('data').of_type(JavaLibrary):
      inputs.append(data.jar_filename)
    for data in target.deps().attr('data').of_type(JavaPrebuilt):
      inputs.append(data.binary_jar)

    command = nodepy.runtime.exec_args + [str(require.resolve('./augjar').filename)]
    command += ['-o', self.jar_filename]

    if self.dist_type == 'merge':
      command += [inputs.pop(0)]  # Merge into the first specified dependency.
      command += ['-s', 'Main-Class=' + self.main_class]
      for infile in inputs:
        command += ['-m', infile]

    else:
      assert self.dist_type == 'onejar'
      command += [ONEJAR_FILENAME]
      command += ['-s', 'One-Jar-Main-Class=' + self.main_class]
      for infile in inputs:
        command += ['-f', 'lib/' + path.base(infile) + '=' + infile]

    if 'jar_dir' not in target.actions:
      mkdir = craftr.actions.Mkdir.new(
        target,
        name = 'jar_dir',
        deps = [],
        directory=self.jar_dir
      )

    craftr.actions.System.new(
      target,
      name = self.dist_type,
      deps = [target.actions.get('jar'), target.actions['jar_dir'], ...],
      commands = [command],
      input_files = inputs,
      output_files = [self.jar_filename]
    )


class JavaPrebuilt(craftr.target.TargetData):
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

  def __init__(self, binary_jar: str = None, artifact: str = None):
    if sum(1 for x in (binary_jar, artifact) if x) != 1:
      raise ValueError('need either binary_jar or artifact argument!')

    if artifact:
      artifact = maven.Artifact.from_id(artifact)
      binary_jar = path.join(session.builddir, '.maven-artifacts', artifact.to_local_path('jar'))
    else:
      binary_jar = craftr.localpath(binary_jar)

    self.binary_jar = binary_jar
    self.artifact = artifact

  def translate(self, target):
    if self.artifact:
      for repo in repos:
        pom = repo.download_pom(self.artifact)
        if pom: break
      else:
        # XXX What error to raise??
        raise RuntimeError('error: could not resolve artifact {}'.format(self.artifact))
      craftr.actions.DownloadFile.new(
        target,
        url = repo.get_artifact_uri(self.artifact, 'jar'),
        filename = self.binary_jar
      )


class ProGuard(craftr.target.TargetData):
  """
  Run ProGuard on the JAR dependencies of this target. If the *pro_file*
  argument is specified, it must be the name of a response file that will
  be passed to the ProGuard commandline.

  The *cwd* will default to the parent directory of *pro_file*, if specified.
  """

  def __init__(self, pro_file=None, options=(), cwd=None, java=None,
               outjars=None):
    self.java = java or session.config.get('java.java', 'java')
    self.pro_file = craftr.localpath(pro_file) if pro_file else None
    if not cwd and self.pro_file:
      cwd = path.dir(self.pro_file)
    self.cwd = craftr.localpath(cwd) if cwd else None
    self.options = options
    self.outjars = outjars

  def translate(self, target):
    injars = []
    for data in target.deps().attr('data'):
      if isinstance(data, JavaPrebuilt):
        injars.append(data.binary_jar)
      elif isinstance(data, (JavaBinary, JavaLibrary)):
        injars.append(data.jar_filename)

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

    craftr.actions.System.new(
      target,
      deps = ...,
      commands = [args],
      input_files = injars,
      output_files = outjars,
      cwd = self.cwd
    )


library = craftr.target_factory(JavaLibrary)
binary = craftr.target_factory(JavaBinary)
prebuilt = craftr.target_factory(JavaPrebuilt)
proguard = craftr.target_factory(ProGuard)


def run(binary, *argv, name=None, java=None, **kwargs):
  kwargs.setdefault('explicit', True)
  target = craftr.T(binary)
  if name is None:
    name = target.name + '_run'
  if java is None:
    java = session.config.get('java.java', 'java')
  command = [java, '-jar', target.data.jar_filename] + list(argv)
  return craftr.gentarget(name = name, deps = [target], commands = [command], **kwargs)
