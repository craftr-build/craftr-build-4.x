
from nr import path
from nr.stream import stream

import copy
import shlex
import sys

import craftr from 'craftr.craftr'
import maven from './tools/maven'
import platform_commands from 'tools.platform-commands.craftr'

ONEJAR_FILENAME = options.onejar
AUGJAR_TOOL = path.join(path.dir(__file__), 'tools', 'augjar.py')
DOWNLOAD_TOOL = path.join(path.dir(__file__), 'tools', 'download.py')



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

      indent = '| ' * depth

      # For now, we use this to avoid downloading the same dependency in
      # different versions, instead only the first version that we find.
      artifact_id = '{}:{}'.format(artifact.group, artifact.artifact)
      if artifact_id in self.poms:
        if parent_deps is not None:
          parent_deps.append(artifact_id)
        print('  {}{} (CACHED)'.format('| ' * depth, artifact))
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

  result = {}
  for source in [path.canonical(x, parent) for x in sources]:
    root = find_src_root(source, src_roots, parent)
    if not root:
      raise ValueError('could not find relative path for {!r} given the '
        'specified root dirs:\n  '.format(source) + '\n  '.join(src_roots))
    rel_root, rel_source = root
    result.setdefault(rel_root, []).append(rel_source)
  return result


def find_src_root(src, roots, parent, allow_curdir=False):
  """
  Finds the source root that *src* is inside and returns it as a tuple of
  (root, rel_path) or #None if the *src* file is not inside any of the
  specified *roots*.
  """

  abs_roots = (path.canonical(x, parent) for x in roots)
  for root, rel_root in zip(abs_roots, roots):
    rel = path.rel(src, root, par=True)
    if allow_curdir and rel == path.curdir or path.issub(rel):
      return rel_root, rel

  return None


class JavaTargetHandler(craftr.TargetHandler):

  name = 'java'

  def __init__(self):
    self.artifacts = ArtifactResolver()
    self.artifact_actions = {}  # Cache to avoid producing the same action multiple times.

  def init(self, context):
    props = context.target_properties
    props.add('java.srcs', craftr.StringList)
    props.add('java.srcRoots', craftr.StringList)
    props.add('java.compilerFlags', craftr.StringList)
    props.add('java.jmod', craftr.Dict[craftr.String, craftr.String])  # A dictionary that maps module names to the module base directories.
    props.add('java.jarName', craftr.String)
    props.add('java.mainClass', craftr.String)
    props.add('java.bundleType', craftr.String)  # The bundle type for applications, can be `none`, `onejar` or `merge`.
    props.add('java.binaryJars', craftr.StringList)
    props.add('java.artifacts', craftr.StringList)
    props.add('java.runArgsPrefix', craftr.StringList)
    props.add('java.runArgs', craftr.StringList)
    props.add('java.jlinkModules', craftr.StringList)  # List of modules to include in the runtime
    props.add('java.jlinkName', craftr.String)  # Directory output name
    props.add('java.jlinkLaunchers', craftr.Dict[craftr.String, craftr.String])  # A dictionary that maps command names to class identifiers in the form "package/class"
    props.add('java.jlinkModulePath', craftr.StringList)
    props.add('java.jlinkFlags', craftr.StringList)

    props = context.dependency_properties
    props.add('java.bundle', craftr.Bool())

  def target_created(self, target):
    target.add_dependency([module.targets['artifacts']])

  def translate_target(self, target):
    src_dir = path.abs(target.directory)
    build_dir = craftr.get_output_directory(target)
    cache_dir = path.join(context.build_directory, module.name, 'artifacts')

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
    jmod = target.get_prop('java.jmod')
    jlinkModules = target.get_prop('java.jlinkModules')
    jlinkName = target.get_prop('java.jlinkName')
    jlinkLaunchers = target.get_prop('java.jlinkLaunchers')
    jlinkModulePath = target.get_prop_join('java.jlinkModulePath')
    jlinkFlags = target.get_prop_join('java.jlinkFlags')

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
            str(artifact).replace(':', '_'), commands=[command],
            input=False, deps=[])
          build = action.add_buildset()
          build.files.add(binary_jar, ['out'])
          self.artifact_actions[binary_jar] = action
          artifactActions.append(action)
        binaryJars.append(binary_jar)
        bundleBinaryJars.append(binary_jar)

    jar_action = None
    javac_action = None
    jmod_actions = []
    bundle_action = None
    jlink_action = None
    run_action = None
    run_bundle_action = None

    classDir = path.join(build_dir, 'cls')
    jarFilename = None
    bundleFilename = None
    jmodFilenames = {}
    jmodDir = path.join(build_dir, 'jmods')

    # Determine all the information necessary to build a java library,
    # and optionally a bundle.
    if srcs:
      srcs = [path.canonical(x, src_dir) for x in srcs]
      if not srcRoots:
        srcRoots = ['src', 'java', 'javatest']
      if not jarName and not jmod:
        jarName = (target.name + '-' + target.module.version)

      # Construct the path to the output JAR file.
      if jarName:
        jarFilename = path.join(build_dir, jarName + '.jar')

      # Construct the bundle filename.
      bundleFilename = None
      if bundleType and jarFilename:
        assert bundleType in ('onejar', 'merge')
        bundleFilename = path.join(build_dir, jarName + '-' + bundleType + '.jar')

      # Construct Java module filenames.
      if jmod:
        for mod_name, mod_dir in jmod.items():
          mod_filename = path.join(jmodDir, mod_name + '.jmod')
          mod_dir = path.canonical(mod_dir, src_dir)
          root = find_src_root(mod_dir, srcRoots, src_dir, allow_curdir=True)
          if not root:
            print('warning: jmod "{}" directory "{}" not in a srcRoot'.format(mod_name, mod_dir))
          else:
            mod_dir = path.join(classDir, root[0], root[1])
          jmod[mod_name] = mod_dir
          jmodFilenames[mod_name] = mod_filename

      # Create a list of all the Java Class files generated by the compiler.
      classFiles = {}
      for root, sources in partition_sources(srcs, srcRoots, src_dir).items():
        classFiles[root] = []
        for src in sources:
          clsfile = path.join(classDir, root, path.setsuffix(src, '.class'))
          classFiles[root].append(clsfile)

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
      binaryJars = list(stream.unique(binaryJars))

    if srcs and classFiles:
      javac_actions = []
      for root, files in classFiles.items():
        # Generate the action to compile the Java source files.
        command = [options.javac]
        if binaryJars:
          command += ['-cp', path.pathsep.join(map(path.abs, binaryJars))]
        command += ['-d', path.join(classDir, root)]
        command += ['$in']
        command += shlex.split(options.compilerFlags) + compilerFlags

        action = target.add_action('java.javac-' + root, commands=[command],
          input=True, deps=artifactActions)

        build = action.add_buildset()
        build.files.add(srcs, ['in'])  # TODO: Select only the files in the current source root
        build.files.add(files, ['out'])

        javac_actions.append(action)

      javac_action = target.add_action('java.javac', commands=[], deps=javac_actions)
      javac_action.add_buildset()

    if jarFilename:
      assert javac_action
      target.outputs.add(jarFilename, ['java.library'])

      # Generate the action to produce the JAR file.
      flags = 'cvf'
      if mainClass:
        flags += 'e'
      command = [options.javacJar, flags, '$out']
      if mainClass:
        command += [mainClass]
      for root in classFiles.keys():
        command += ['-C', path.join(classDir, root), '.']
      jar_action = target.add_action('java.jar', commands=[command], deps=[javac_action])
      build = jar_action.add_buildset()
      build.files.add(stream.concat(classFiles.values()), ['in'])
      build.files.add(jarFilename, ['out'])

    # Generate actions to build Java modules.
    if jmod:
      for mod_name, mod_dir in jmod.items():
        # TODO: Determine the class actions that produce the mentioned class
        #       files so we can add them as dependencies -- allowing the build
        #       backend to determine when the rule needs to be rebuilt.

        mod_filename = jmodFilenames[mod_name]
        commands = []
        commands.append(platform_commands.rm(mod_filename, force=True))
        commands.append(['jmod', 'create', '--class-path', mod_dir, mod_filename])
        action = target.add_action('java.jmod-' + mod_name, commands=commands, deps=[javac_action])
        buildset = action.add_buildset()
        #buildset.files.add(..., ['in', 'java.class'])
        buildset.files.add(mod_filename, ['out', 'java.jmod'])
        jmod_actions.append(action)

      action = target.add_action('java.jmod', commands=[['echo']], deps=jmod_actions)
      action.add_buildset()

    # Generate the action to produce a merge of all dependent JARs if
    # so specified in the target.
    if bundleType and bundleFilename:
      target.outputs.add(bundleFilename, ['java.bundle'])

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

    if jlinkModules:
      jlinkModulePath = list(jlinkModulePath)
      jlinkModulePath.append(jmodDir)  # TODO: Append jmodDir of all dependencies

      # TODO: Collect actions that produce the modules -- possibly from
      # dependent targets and not just this target (thus, just jmod_actions
      # may not be sufficient).

      if not jlinkName:
        jlinkName = target.name + '-' + target.module.version + '-runtime'
      if not path.isabs(jlinkName):
        jlinkName = path.join(build_dir, jlinkName)

      commands = []
      # Make sure the previous directory does not exist.
      commands.append(platform_commands.rm(jlinkName, recursive=True, force=True))
      # Generate the jlink command/
      commands.append(['jlink'])
      commands[-1] += ['--module-path', jmodDir]
      commands[-1] += ['--add-modules'] + jlinkModules
      commands[-1] += ['--output', jlinkName]
      for command, module in jlinkLaunchers.items():
        commands[-1] += ['--launcher', '{}={}'.format(command, module)]
      commands[-1] += jlinkFlags

      jlink_action = target.add_action('java.jlink', commands=commands,
        deps=jmod_actions + [jar_action], explicit=True, syncio=True, output=True)
      build = jlink_action.add_buildset()
      # TODO: Determine input/output files?

    if (len(jmod) == 1 or jarFilename) and mainClass:
      # An action to execute the library JAR (with the proper classpath).
      if jarFilename:
        command = list(runArgsPrefix or ['java'])
        classpath = binaryJars + [jarFilename]
        command += ['-cp', path.pathsep.join(classpath)]
        command += [mainClass] + runArgs
      else:
        command = list(runArgsPrefix or ['java'])
        command += ['-p', path.pathsep.join([jmodDir])]  # TODO: Additional JMOD dirs?
        command += ['-cp', path.pathsep.join(binaryJars)]
        mod_name = next(iter(jmod))
        command += ['-m', mod_name + '/' + mainClass] + runArgs

      run_action = target.add_action('java.run', commands=[command],
        deps=[jar_action] + jmod_actions, explicit=True, syncio=True, output=False)
      run_action.add_buildset()

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
      run_bundle_action = target.add_action('java.runBundle', commands=[command],
        deps=[bundle_action], explicit=True, syncio=True, output=False)
      run_bundle_action.add_buildset()


context.register_handler(JavaTargetHandler())
