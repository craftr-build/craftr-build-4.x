
import copy
import craftr
import shlex
import sys
from nr import path

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

  name = 'java'

  def __init__(self):
    self.artifacts = ArtifactResolver()
    self.artifact_actions = {}  # Cache to avoid producing the same action multiple times.

  def init(self, context):
    props = context.target_properties
    props.add('java.srcs', craftr.StringList())
    props.add('java.srcRoots', craftr.StringList())
    props.add('java.compilerFlags', craftr.StringList())
    props.add('java.jarName', craftr.String())
    props.add('java.mainClass', craftr.String())
    props.add('java.bundleType', craftr.String())  # The bundle type for applications, can be `none`, `onejar` or `merge`.
    props.add('java.binaryJars', craftr.StringList())
    props.add('java.artifacts', craftr.StringList())
    props.add('java.runArgsPrefix', craftr.StringList())
    props.add('java.runArgs', craftr.StringList())

    props = context.dependency_properties
    props.add('java.bundle', craftr.Bool())

  def translate_target(self, target):
    src_dir = path.abs(target.directory)
    build_dir = path.join(context.build_directory, target.module.name)
    cache_dir = path.join(context.build_directory, module.name, 'artifacts')

    jarFilename = None
    bundleFilename = None
    binaryJars = target.get_prop_join('java.binaryJars')
    nobundleBinaryJars = []
    bundleBinaryJars = binaryJars
    artifacts = target.get_prop_join('java.artifacts')
    srcs = target.get_prop_join('java.srcs')
    srcRoots = target.get_prop_join('java.srcRoots')
    jarName = target.get_prop('java.jarName')
    bundleType = target.get_prop('java.bundleType')
    compilerFlags = target.get_prop_join('java.compilerFlags')
    mainClass = target.get_prop('java.mainClass')
    runArgs = target.get_prop_join('java.runArgs')
    runArgsPrefix = target.get_prop('java.runArgsPrefix')

    # Add actions that download the artifacts.
    artifactActions = []
    if artifacts:
      print('[{}] Resolving JARs...'.format(target.id))
      for artifact, repo in self.artifacts.resolve(artifacts):
        binary_jar = path.join(cache_dir, artifact.to_local_path('jar'))
        if binary_jar in self.artifact_actions:
          artifactActions.append(self.artifact_actions[binary_jar])
        else:
          # TODO: We could theortically model this with a single action
          #       and multiple build sets.
          command = [sys.executable, DOWNLOAD_TOOL]
          command += [binary_jar]
          command += [repo.get_artifact_uri(artifact, 'jar')]
          action = module.targets['artifacts'].add_action(
            str(artifact).replace(':', '_'), commands=[command])
          build = action.add_buildset()
          build.files.add(binary_jar, ['out'])
          self.artifact_actions[binary_jar] = action
          artifactActions.append(action)
        binaryJars.append(binary_jar)
        bundleBinaryJars.append(binary_jar)

    # Determine all the information necessary to build a java library,
    # and optionally a bundle.
    if srcs:
      srcs = [path.canonical(x, src_dir) for x in srcs]
      if not srcRoots:
        srcRoots = ['src', 'java', 'javatest']
      if not jarName:
        jarName = (target.name + '-' + target.module.version)

      # Construct the path to the output JAR file.
      jarFilename = path.join(build_dir, jarName + '.jar')
      bundleFilename = None
      if bundleType:
        assert bundleType in ('onejar', 'merge')
        bundleFilename = path.join(build_dir, jarName + '-' + bundleType + '.jar')

      # Create a list of all the Java Class files generated by the compiler.
      classDir = path.join(build_dir, 'cls')
      classFiles = []
      for root, sources in partition_sources(srcs, srcRoots,
                                            target.directory).items():
        for src in sources:
          clsfile = path.join(classDir, path.setsuffix(src, '.class'))
          classFiles.append(clsfile)

      target.outputs.add(jarFilename, ['java.library'])
      if bundleFilename:
        target.outputs.add(bundleFilename, ['java.bundle'])

      # Add to the binaryJars the Java libraries from dependencies.
      for dep in target.transitive_dependencies():
        doBundle = dep.props['java.bundle']
        for dep_target in dep.sources:
          libs = dep_target.outputs.tagged('java.library')
          binaryJars += libs
          if doBundle:
            bundleBinaryJars += libs
          else:
            nobundleBinaryJars += libs

    if srcs and classFiles:
      # Generate the action to compile the Java source files.
      command = [options.javac, '-d', classDir]
      if binaryJars:
        command += ['-classpath', path.pathsep.join(binaryJars)]
      command += ['$in']
      command += shlex.split(options.compilerFlags) + compilerFlags
      action = target.add_action('java.javac', commands=[command],
        input=True, deps=artifactActions)
      build = action.add_buildset()
      build.files.add(srcs, ['in'])
      build.files.add(classFiles, ['out'])

      # Generate the action to produce the JAR file.
      flags = 'cvf'
      if mainClass:
        flags += 'e'
      command = [options.javacJar, flags, '$out']
      if mainClass:
        command += [mainClass]
      command += ['-C', classDir, '.']
      jar_action = target.add_action('java.jar', commands=[command])
      build = jar_action.add_buildset()
      build.files.add(classFiles, ['in'])
      build.files.add(jarFilename, ['out'])

    # Generate the action to produce a merge of all dependent JARs if
    # so specified in the target.
    if bundleType and bundleFilename:
      command = [sys.executable, AUGJAR_TOOL, '-o', '$out']
      inputs = [jarFilename] + bundleBinaryJars
      if bundleType == 'merge':
        command += [inputs[0], '-s', 'Main-Class=' + mainClass]
        for infile in inputs[1:]:
          command += ['-m', infile]
      elif bundleType == 'onejar':
        command += [ONEJAR_FILENAME, '-s', 'One-Jar-Main-Class=' + mainClass]
        for infile in inputs:
          command += ['-f', 'lib/' + path.base(infile) + '=' + infile]
        inputs += [ONEJAR_FILENAME]
      else:
        raise ValueError('invalid bundleType: {!r}'.format(bundleType))
      bundle_action = target.add_action('java.bundle', commands=[command])
      build = bundle_action.add_buildset()
      build.files.add(inputs, ['in'])
      build.files.add(bundleFilename, ['out'])

    if jarFilename and mainClass:
      # An action to execute the library JAR (with the proper classpath).
      command = list(runArgsPrefix or ['java'])
      classpath = binaryJars + [jarFilename]
      command += ['-cp', path.pathsep.join(classpath)]
      command += [mainClass] + runArgs
      action = target.add_action('java.run', commands=[command],
        deps=[jar_action], explicit=True, syncio=True, output=False)
      action.add_buildset()

    if bundleFilename and mainClass:
      # An action to execute the bundled JAR.
      command = list(runArgsPrefix or ['java'])
      if not nobundleBinaryJars:
        command += ['-jar', bundleFilename]
      else:
        classpath = nobundleBinaryJars + [bundleFilename]
        command += ['-cp', path.pathsep.join(classpath)]
        command += ['com.simontuffs.onejar.Boot' if bundleType == 'onejar' else mainClass]
      command += runArgs
      action = target.add_action('java.runBundle', commands=[command],
        deps=[bundle_action], explicit=True, syncio=True, output=False)
      action.add_buildset()


context.register_handler(JavaTargetHandler())
