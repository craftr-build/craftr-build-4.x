
import copy
import craftr
import sys
from craftr import path

ONEJAR_FILENAME = path.join(path.dir(__file__), 'tools', 'one-jar-boot-0.97.jar')
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
    self.repos.append(maven.MavenRepository('default', 'http://repo1.maven.org/maven2/'))

  def resolve(self, artifacts):
    """
    Resolves all artifacts in the *artifacts* list (which must be strings or
    #maven.Artifacts objects). Returns a list of (Artifact, MavenRepository)
    objects.
    """

    queue = [(0, x) for x in reversed(artifacts)]
    result = []

    while queue:
      depth, artifact = queue.pop()
      if isinstance(artifact, str):
        artifact = maven.Artifact.from_id(artifact)
      if artifact.scope != 'compile' or artifact.type != 'jar':
        continue

      # For now, we use this to avoid downloading the same dependency in
      # different versions, instead only the first version that we find.
      artifact_id = '{}:{}'.format(artifact.group, artifact.artifact)
      if artifact_id in self.poms:
        result.append((artifacts, self.poms[artifact_id][2]))
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
      self.poms[artifact_id] = (artifact, pom, repo)
      result.append((artifact, repo))
      queue.extend([(depth+1, x) for x in reversed(maven.pom_eval_deps(pom))])

      # Print dependency info.
      indent = '| ' * depth
      print('  {}{} ({})'.format('| ' * depth, artifact, repo.name))

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
        'specified root dirs:\n  '.format(source) + '\n  '.join(base_dirs))
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
    # Whether to embedd the library when combining JARs. Defaults
    # to True for applicaton JARs, False to library JARs.
    target.define_property('java.embed', 'Bool')

  def finalize_target(self, target, data):
    build_dir = path.join(context.build_directory, target.module().name())
    cache_dir = path.join(context.build_directory, module.name(), 'artifacts')

    data.jarFilename = None
    data.bundleFilename = None

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
          data.artifactActions.append(action)
        data.binaryJars.append(binary_jar)

    # Determine all the information necessary to build a java library,
    # and optionally a bundle.
    if data.srcs:
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

  def translate_target(self, target, data):
    if data.srcs and data.classFiles:
      # Generate the action to compile the Java source files.
      command = [javac, '-d', data.classDir]
      if data.binaryJars:
        command += ['-classpath', path.pathsep.join(data.binaryJars)]
      command += ['$in']
      command += data.compilerFlags
      action = target.add_action('java.javac', commands=[command], deps=data.artifactActions)
      build = action.add_buildset()
      build.files.add(data.srcs, ['in'])
      build.files.add(data.classFiles, ['out'])

      # Generate the action to produce the JAR file.
      flags = 'cvf'
      if data.mainClass:
        flags += 'e'
      command = [javacJar, flags, '$out']
      if data.mainClass:
        command += [data.mainClass]
      command += ['-C', data.classDir, '.']
      action = target.add_action('java.jar', commands=[command])
      build = action.add_buildset()
      build.files.add(data.classFiles, ['in'])
      build.files.add(data.jarFilename, ['out'])

    # Generate the action to produce a merge of all dependent JARs if
    # so specified in the target.
    if data.bundleType and data.bundleFilename:
      command = [sys.executable, AUGJAR_TOOL, '-o', '$out']
      inputs = [data.jarFilename] + data.binaryJars
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
      action = target.add_action('java.bundle', commands=[command])
      build = action.add_buildset()
      build.files.add(inputs, ['in'])
      build.files.add(data.bundleFilename, ['out'])

    if data.jarFilename or data.bundleFilename:
      # An action to execute the JAR file.
      command = (data.runPrefix or ['java']) + ['-jar', data.bundleFilename or data.jarFilename]
      action = target.add_action('java.run', commands=[command], explicit=True, syncio=True)
      action.add_buildset()


module.register_target_handler(JavaTargetHandler())
