
import copy
import craftr
import shlex
import sys
from craftr import path

ONEJAR_FILENAME = options.onejar
AUGJAR_TOOL = path.join(path.dir(__file__), 'tools', 'augjar.py')
DOWNLOAD_TOOL = path.join(path.dir(__file__), 'tools', 'download.py')
maven = load('./tools/maven.py')


class ArtifactResolver:
  """
  Helper structure to resolve Maven Artifacts.
  """

  def __init__(self):
    self.poms = {}
    self.repos = []

    repo_config = context.options.get('java', {}).get('repos', {})
    if 'default' not in repo_config:
      self.repos.append(maven.MavenRepository('default', 'http://repo1.maven.org/maven2/'))
    for key, value in repo_config.items():
      self.repos.append(maven.MavenRepository(key, value))

  def resolve(self, artifacts):
    """
    Resolves all artifacts in the *artifacts* list (which must be strings or
    #maven.Artifacts objects). Returns a list of (Artifact, MavenRepository)
    objects.
    """


    artifacts = [maven.Artifact.from_id(x) if isinstance(x, str) else x
                 for x in artifacts]
    queue = [(0, x, None) for x in reversed(artifacts)]

    while queue:
      depth, artifact, parent_deps = queue.pop()
      if isinstance(artifact, str):
        artifact = maven.Artifact.from_id(artifact)
      if artifact.scope != 'compile' or artifact.type != 'jar':
        continue

      # For now, we use this to avoid downloading the same dependency in
      # different versions, instead only the first version that we find.
      artifact_id = '{}:{}'.format(artifact.group, artifact.artifact)
      if artifact_id in self.poms:
        if parent_deps is not None:
          parent_deps.append(artifact_id)
        continue

      # Try to find a POM manifest for the artifact.
      for repo in self.repos:
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
      if parent_deps is not None:
        parent_deps.append(artifact_id)
      deps = []
      self.poms[artifact_id] = (artifact, pom, repo, deps)
      queue.extend([(depth+1, x, deps) for x in reversed(maven.pom_eval_deps(pom))])

      # Print dependency info.
      indent = '| ' * depth
      print('  {}{} ({})'.format('| ' * depth, artifact, repo.name))

    seen = set()
    result = []
    def recurse_add(artifact_id):
      if artifact_id in seen:
        return
      seen.add(artifact_id)
      artifact, pom, repo, deps = self.poms[artifact_id]
      result.append((artifact, repo))
      for artifact_id in deps:
        recurse_add(artifact_id)
    for a in artifacts:
      artifact_id = '{}:{}'.format(a.group, a.artifact)
      recurse_add(artifact_id)

    return result


def partition_sources(sources, src_roots, parent):
  """
  Partitions a set of files in *sources* to the appropriate parent directory
  in *src_roots*. If a file is found that is not located in one of the
  *src_roots*, a #ValueError is raised.

  A relative path in *sources* and *src_roots* will be automatically converted
  to an absolute path using the *parent*, which defaults to the currently
  executed module's directory.
  """

  abs_roots = [path.canonical(x, parent) for x in src_roots]
  result = {}
  for source in [path.canonical(x, parent) for x in sources]:
    for root, rel_root in zip(abs_roots, src_roots):
      rel_source = path.rel(source, root)
      if path.isrel(rel_source):
        break
    else:
      raise ValueError('could not find relative path for {!r} given the '
        'specified root dirs:\n  '.format(source) + '\n  '.join(src_roots))
    result.setdefault(rel_root, []).append(rel_source)
  return result


class JavaTargetHandler(craftr.TargetHandler):

  def __init__(self):
    self.artifacts = ArtifactResolver()
    self.artifact_actions = {}  # Cache to avoid producing the same action multiple times.

  def get_common_property_scope(self):
    return 'java'

  def setup_target(self, target):
    target.define_property('java.srcs', 'StringList', inheritable=False)
    target.define_property('java.srcRoots', 'StringList', inheritable=False)
    target.define_property('java.compilerFlags', 'StringList')
    target.define_property('java.jarName', 'String', inheritable=False)
    target.define_property('java.mainClass', 'String', inheritable=False)
    target.define_property('java.bundleType', 'String')  # The bundle type for applications, can be `none`, `onejar` or `merge`.
    target.define_property('java.binaryJars', 'StringList')
    target.define_property('java.artifacts', 'StringList')
    target.define_property('java.runPrefix', 'StringList', inheritable=False)
    target.define_property('java.run', 'StringList', inheritable=False)

  def setup_dependency(self, target):
    # Whether to include the library in a bundle.
    target.define_property('java.bundle', 'Bool')

  def finalize_target(self, target, data):
    src_dir = path.abs(target.directory())
    build_dir = path.join(context.build_directory, target.module().name())
    cache_dir = path.join(context.build_directory, module.name(), 'artifacts')

    data.jarFilename = None
    data.bundleFilename = None
    data.nobundleBinaryJars = []
    data.bundleBinaryJars = data.binaryJars[:]

    # Add actions that download the artifacts.
    data.artifactActions = []
    if data.artifacts:
      print('[{}] Resolving JARs...'.format(target.identifier()))
      for artifact, repo in self.artifacts.resolve(data.artifacts):
        binary_jar = path.join(cache_dir, artifact.to_local_path('jar'))
        if binary_jar in self.artifact_actions:
          data.artifactActions.append(self.artifact_actions[binary_jar])
        else:
          # TODO: We could theortically model this with a single action
          #       and multiple build sets.
          command = [sys.executable, DOWNLOAD_TOOL]
          command += [binary_jar]
          command += [repo.get_artifact_uri(artifact, 'jar')]
          action = module.target('artifacts').add_action(
            str(artifact).replace(':', '_'), commands=[command])
          build = action.add_buildset()
          build.files.add(binary_jar, ['out'])
          self.artifact_actions[binary_jar] = action
          data.artifactActions.append(action)
        data.binaryJars.append(binary_jar)
        data.bundleBinaryJars.append(binary_jar)

    # Determine all the information necessary to build a java library,
    # and optionally a bundle.
    if data.srcs:
      data.srcs = [path.canonical(x, src_dir) for x in data.srcs]
      if not data.srcRoots:
        data.srcRoots = ['src', 'java', 'javatest']
      if not data.jarName:
        data.jarName = (target.name() + '-' + target.module().version())

      # Construct the path to the output JAR file.
      data.jarFilename = path.join(build_dir, data.jarName + '.jar')
      data.bundleFilename = None
      if data.bundleType:
        assert data.bundleType in ('onejar', 'merge')
        data.bundleFilename = path.join(build_dir, data.jarName + '-' + data.bundleType + '.jar')

      # Create a list of all the Java Class files generated by the compiler.
      data.classDir = path.join(build_dir, 'cls')
      data.classFiles = []
      for root, sources in partition_sources(data.srcs, data.srcRoots,
                                            target.directory()).items():
        for src in sources:
          clsfile = path.join(data.classDir, path.setsuffix(src, '.class'))
          data.classFiles.append(clsfile)

      target.outputs().add(data.jarFilename, ['java.library'])
      if data.bundleFilename:
        target.outputs().add(data.bundleFilename, ['java.bundle'])

      # Add to the binaryJars the Java libraries from dependencies.
      for dep in target.transitive_dependencies():
        depData = dep.handler_data(self)
        for target in dep.targets():
          libs = target.outputs().tagged('java.library')
          data.binaryJars += libs
          if depData.bundle:
            data.bundleBinaryJars += libs
          else:
            data.nobundleBinaryJars += libs

  def translate_target(self, target, data):
    if data.srcs and data.classFiles:
      # Generate the action to compile the Java source files.
      command = [options.javac, '-d', data.classDir]
      if data.binaryJars:
        command += ['-classpath', path.pathsep.join(data.binaryJars)]
      command += ['$in']
      command += shlex.split(options.compilerFlags) + data.compilerFlags
      action = target.add_action('java.javac', commands=[command],
        input=True, deps=data.artifactActions)
      build = action.add_buildset()
      build.files.add(data.srcs, ['in'])
      build.files.add(data.classFiles, ['out'])

      # Generate the action to produce the JAR file.
      flags = 'cvf'
      if data.mainClass:
        flags += 'e'
      command = [options.javacJar, flags, '$out']
      if data.mainClass:
        command += [data.mainClass]
      command += ['-C', data.classDir, '.']
      jar_action = target.add_action('java.jar', commands=[command])
      build = jar_action.add_buildset()
      build.files.add(data.classFiles, ['in'])
      build.files.add(data.jarFilename, ['out'])

    # Generate the action to produce a merge of all dependent JARs if
    # so specified in the target.
    if data.bundleType and data.bundleFilename:
      command = [sys.executable, AUGJAR_TOOL, '-o', '$out']
      inputs = [data.jarFilename] + data.bundleBinaryJars
      if data.bundleType == 'merge':
        command += [inputs[0], '-s', 'Main-Class=' + data.mainClass]
        for infile in inputs[1:]:
          command += ['-m', infile]
      elif data.bundleType == 'onejar':
        command += [ONEJAR_FILENAME, '-s', 'One-Jar-Main-Class=' + data.mainClass]
        for infile in inputs:
          command += ['-f', 'lib/' + path.base(infile) + '=' + infile]
        inputs += [ONEJAR_FILENAME]
      else:
        raise ValueError('invalid bundleType: {!r}'.format(data.bundleType))
      bundle_action = target.add_action('java.bundle', commands=[command])
      build = bundle_action.add_buildset()
      build.files.add(inputs, ['in'])
      build.files.add(data.bundleFilename, ['out'])

    if data.jarFilename and data.mainClass:
      # An action to execute the library JAR (with the proper classpath).
      command = list(data.runPrefix or ['java'])
      classpath = data.binaryJars + [data.jarFilename]
      command += ['-cp', path.pathsep.join(classpath)]
      command += [data.mainClass]
      action = target.add_action('java.run', commands=[command],
        deps=[jar_action], explicit=True, syncio=True, output=False)
      action.add_buildset()

    if data.bundleFilename and data.mainClass:
      # An action to execute the bundled JAR.
      command = list(data.runPrefix or ['java'])
      if not data.nobundleBinaryJars:
        command += ['-jar', data.bundleFilename]
      else:
        classpath = data.nobundleBinaryJars + [data.bundleFilename]
        command += ['-cp', path.pathsep.join(classpath)]
        command += ['com.simontuffs.onejar.Boot' if data.bundleType == 'onejar' else data.mainClass]
      action = target.add_action('java.runBundle', commands=[command],
        deps=[bundle_action], explicit=True, syncio=True, output=False)
      action.add_buildset()


module.register_target_handler(JavaTargetHandler())
